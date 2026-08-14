from __future__ import annotations

from typing import Any

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]

PROJECT_ID = 1
REQUIREMENT_ID = 17


def _json_200(response: requests.Response, context: str) -> Any:
    assert response.status_code == 200, f"{context} returned {response.status_code}: {response.text[:300]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def _assert_has_payload(payload: Any, context: str) -> None:
    assert payload is not None, f"{context} returned an empty JSON payload"
    if isinstance(payload, dict):
        assert payload, f"{context} returned an empty JSON object"


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/dashboards/data/overview", {"role_type": "ADMIN"}, id="overview"),
        pytest.param("/api/v1/dashboards/data/statistics/summary", {"role_type": "ADMIN"}, id="statistics_summary"),
        pytest.param("/api/v1/dashboards/data/metrics/projects", {"time_range": "30d"}, id="project_metrics"),
        pytest.param("/api/v1/dashboards/data/metrics/quality", {"time_range": "30d"}, id="quality_metrics"),
        pytest.param("/api/v1/dashboards/data/real-time/system_status", {}, id="realtime_system_status"),
        pytest.param("/api/v1/dashboards/data/trends/project_progress", {"time_range": "30d"}, id="project_progress_trend"),
        pytest.param("/api/v1/dashboards/data/trends/test_pass_rate", {"time_range": "30d"}, id="test_pass_rate_trend"),
    ],
)
def test_dashboard_data_business_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    payload = _json_200(authenticated_session.get(f"{base_url}{path}", params=params, timeout=15), path)

    _assert_has_payload(payload, path)


def test_quality_metric_dashboard_and_health_are_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    dashboard = _json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/quality-metrics/dashboard",
            params={"project_id": PROJECT_ID},
            timeout=15,
        ),
        "quality dashboard",
    )
    _assert_has_payload(dashboard, "quality dashboard")

    health = _json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/quality-metrics/health-check",
            params={"project_id": PROJECT_ID},
            timeout=15,
        ),
        "quality health check",
    )
    _assert_has_payload(health, "quality health check")


@pytest.mark.parametrize(
    ("path", "body"),
    [
        pytest.param(
            "/api/v1/quality-metrics/calculate",
            {"project_id": PROJECT_ID, "metrics": ["test_pass_rate", "defect_density"], "include_trends": True},
            id="calculate_quality",
        ),
        pytest.param(
            "/api/v1/quality-metrics/trends/analyze",
            {
                "project_id": PROJECT_ID,
                "metrics": ["test_pass_rate"],
                "analysis_period_days": 30,
                "include_predictions": False,
            },
            id="analyze_trends",
        ),
        pytest.param(
            "/api/v1/quality-metrics/improvements/suggest",
            {"project_id": PROJECT_ID, "focus_areas": ["testing"], "priority_level": "high"},
            id="suggest_improvements",
        ),
    ],
)
def test_quality_metric_business_actions_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    body: dict[str, Any],
) -> None:
    payload = _json_200(authenticated_session.post(f"{base_url}{path}", json=body, timeout=20), path)

    _assert_has_payload(payload, path)


def test_requirement_traceability_business_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    links = _json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/requirement-traceability/links",
            params={"project_id": PROJECT_ID, "skip": 0, "limit": 20},
            timeout=15,
        ),
        "traceability links",
    )
    _assert_has_payload(links, "traceability links")

    requirement_view = _json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/requirement-traceability/requirements/{REQUIREMENT_ID}",
            timeout=15,
        ),
        "requirement traceability",
    )
    _assert_has_payload(requirement_view, "requirement traceability")

    coverage = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/requirement-traceability/coverage/{PROJECT_ID}", timeout=15),
        "traceability coverage",
    )
    _assert_has_payload(coverage, "traceability coverage")


def test_requirement_traceability_matrix_generation_returns_json(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    payload = _json_200(
        authenticated_session.post(
            f"{base_url}/api/v1/requirement-traceability/matrix",
            json={"project_id": PROJECT_ID, "matrix_type": "requirement_to_test", "include_indirect": False},
            timeout=20,
        ),
        "traceability matrix",
    )

    _assert_has_payload(payload, "traceability matrix")


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/prompt-templates/", {"page": 1, "size": 10}, id="template_list"),
        pytest.param("/api/v1/prompt-templates/categories", {}, id="template_categories"),
        pytest.param("/api/v1/prompt-templates/visibility-options", {}, id="template_visibility_options"),
        pytest.param("/api/v1/prompt-templates/statistics/overview", {}, id="template_statistics"),
        pytest.param("/api/v1/prompt-templates/user/my-templates", {"page": 1, "size": 10}, id="my_templates"),
    ],
)
def test_prompt_template_business_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    payload = _json_200(authenticated_session.get(f"{base_url}{path}", params=params, timeout=15), path)

    _assert_has_payload(payload, path)


def test_prompt_template_search_returns_json(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    payload = _json_200(
        authenticated_session.post(
            f"{base_url}/api/v1/prompt-templates/search",
            json={"query": "login", "page": 1, "size": 10},
            timeout=15,
        ),
        "prompt template search",
    )

    _assert_has_payload(payload, "prompt template search")


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/api/v1/ai-assistant/status", id="assistant_status"),
        pytest.param("/api/v1/ai-assistant/health", id="assistant_health"),
        pytest.param("/api/v1/ai-assistant/services/info", id="assistant_services"),
        pytest.param("/api/v1/ai-assistant/conversations", id="assistant_conversations"),
        pytest.param("/api/v1/ai-assistant/conversations/stats", id="assistant_conversation_stats"),
    ],
)
def test_ai_assistant_workspace_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    payload = _json_200(authenticated_session.get(f"{base_url}{path}", params={"page": 1, "size": 10}, timeout=15), path)

    _assert_has_payload(payload, path)
