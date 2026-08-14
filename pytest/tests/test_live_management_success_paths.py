from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


CONFIG_KEY = "codex.page.check.1780371232"
ENVIRONMENT = "prod"


def _assert_json_200(response: requests.Response, path: str) -> dict:
    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def _first_data_item(payload: dict, label: str) -> dict:
    items = payload.get("data")
    if isinstance(items, dict):
        items = items.get("items")
    if not isinstance(items, list) or not items:
        pytest.skip(f"No existing {label} record is available for read-only detail coverage.")
    return items[0]


def test_execution_detail_and_logs_are_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    execution_list = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/test-executions/", timeout=15),
        "/api/v1/test-executions/",
    )
    execution_id = _first_data_item(execution_list, "test execution")["id"]

    detail = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/test-executions/{execution_id}", timeout=15),
        f"/api/v1/test-executions/{execution_id}",
    )
    assert detail["data"]["id"] == execution_id

    logs = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/test-executions/{execution_id}/logs", timeout=15),
        f"/api/v1/test-executions/{execution_id}/logs",
    )
    assert isinstance(logs["data"], list)


def test_defect_detail_and_comments_are_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    defect_list = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/defects/", timeout=15),
        "/api/v1/defects/",
    )
    defect_id = _first_data_item(defect_list, "defect")["id"]

    defect = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/defects/{defect_id}", timeout=15),
        f"/api/v1/defects/{defect_id}",
    )
    assert defect["data"]["id"] == defect_id

    comments = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/defects/{defect_id}/comments", timeout=15),
        f"/api/v1/defects/{defect_id}/comments",
    )
    assert "total" in comments
    assert isinstance(comments["data"], list)


def test_config_read_paths_are_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    config_list = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/configs/configs", timeout=15),
        "/api/v1/configs/configs",
    )
    assert config_list["data"]["items"]

    config_detail = _assert_json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/configs/configs/{CONFIG_KEY}",
            params={"environment": ENVIRONMENT, "decrypt": False},
            timeout=15,
        ),
        f"/api/v1/configs/configs/{CONFIG_KEY}",
    )
    assert config_detail["data"]["config_key"] == CONFIG_KEY

    env_stats = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/configs/environments/{ENVIRONMENT}/statistics", timeout=15),
        f"/api/v1/configs/environments/{ENVIRONMENT}/statistics",
    )
    assert env_stats["data"]["environment"] == ENVIRONMENT

    formats = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/configs/import-export/formats", timeout=15),
        "/api/v1/configs/import-export/formats",
    )
    assert "env" in formats["data"]

    rule_templates = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/configs/validation-rules/rule-templates", timeout=15),
        "/api/v1/configs/validation-rules/rule-templates",
    )
    assert isinstance(rule_templates["data"], list)

    advanced_templates = _assert_json_200(
        authenticated_session.get(f"{base_url}/api/v1/configs/advanced-permissions/templates", timeout=15),
        "/api/v1/configs/advanced-permissions/templates",
    )
    assert isinstance(advanced_templates["data"], list)

    effective = _assert_json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/configs/advanced-permissions/user/1/effective",
            params={"config_key": CONFIG_KEY, "environment": ENVIRONMENT},
            timeout=15,
        ),
        "/api/v1/configs/advanced-permissions/user/1/effective",
    )
    assert "column_level" in effective["data"]

    permission_check = _assert_json_200(
        authenticated_session.get(
            f"{base_url}/api/v1/configs/permissions/check",
            params={"config_key": CONFIG_KEY, "environment": ENVIRONMENT, "action": "READ"},
            timeout=15,
        ),
        "/api/v1/configs/permissions/check",
    )
    assert "has_permission" in permission_check["data"]
