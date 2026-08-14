from __future__ import annotations

import csv
import datetime as dt
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import requests

from conftest import LiveCleanupStack, csv_login_admin_from_csv


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "test_cases" / "business_crud_case_data.csv"
AUTO_PREFIX = "PYTEST_AUTO"
PROJECT_ID = 1
ADMIN_USER_ID = 1
REQUIRED_COLUMNS = {
    "case_id",
    "module",
    "case_type",
    "operation",
    "description",
    "login_payload",
    "create_payload",
    "update_payload",
    "expected_login_status",
    "expected_create_status",
    "expected_read_status",
    "expected_update_status",
    "expected_delete_status",
    "expected_deleted_read_status",
}


def _load_cases() -> list[dict[str, str]]:
    if not DATA_PATH.exists():
        pytest.fail(f"Business CRUD case data does not exist: {DATA_PATH}", pytrace=False)

    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            pytest.fail(f"Business CRUD case data missing columns: {sorted(missing)}")
        return list(reader)


CASES = _load_cases()
LOGIN_CASES = [case for case in CASES if case["module"] == "auth" and case["operation"] == "login"]
CRUD_CASES = [case for case in CASES if case["module"] != "auth"]


def _case_id(case: dict[str, str]) -> str:
    return f"{case['module']} {case['case_type']} {case['operation']} {case['case_id']}"


def _json_field(case: dict[str, str], column: str) -> dict[str, Any]:
    raw = case[column].strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{case['case_id']} has invalid JSON in {column}: {exc}")
    assert isinstance(payload, dict), f"{case['case_id']} {column} must be a JSON object"
    return payload


def _replace_placeholders(value: Any, replacements: dict[str, Any]) -> Any:
    if isinstance(value, str):
        for placeholder, replacement in replacements.items():
            if value == placeholder:
                return replacement
        rendered = value
        for placeholder, replacement in replacements.items():
            rendered = rendered.replace(placeholder, str(replacement))
        return rendered
    if isinstance(value, list):
        return [_replace_placeholders(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_placeholders(item, replacements) for key, item in value.items()}
    return value


def _case_context(case: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    suffix = uuid.uuid4().hex[:10]
    label = case["module"].upper().replace("-", "_")
    unique = f"{AUTO_PREFIX}_{label}_{suffix}"
    start_time = (dt.datetime.utcnow() + dt.timedelta(days=30)).replace(microsecond=0)
    end_time = start_time + dt.timedelta(hours=1)
    future_date = (dt.date.today() + dt.timedelta(days=90)).isoformat()
    future_date_plus_one = (dt.date.today() + dt.timedelta(days=91)).isoformat()
    replacements = {
        "{{unique}}": unique,
        "{{unique_lower}}": unique.lower(),
        "{{unique_upper}}": unique.upper(),
        "{{unique_suffix}}": suffix,
        "{{project_id}}": PROJECT_ID,
        "{{admin_user_id}}": ADMIN_USER_ID,
        "{{future_start}}": start_time.isoformat(),
        "{{future_end}}": end_time.isoformat(),
        "{{future_date}}": future_date,
        "{{future_date_plus_one}}": future_date_plus_one,
    }
    path_vars: dict[str, Any] = {
        "project_id": PROJECT_ID,
        "admin_user_id": ADMIN_USER_ID,
        "unique_suffix": suffix,
    }
    return replacements, path_vars


def _set_context_value(
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
    name: str,
    value: Any,
) -> None:
    replacements[f"{{{{{name}}}}}"] = value
    path_vars[name] = value


def _render_json_field(case: dict[str, str], column: str, replacements: dict[str, Any]) -> dict[str, Any]:
    rendered = _replace_placeholders(_json_field(case, column), replacements)
    assert isinstance(rendered, dict)
    return rendered


def _render_login_payload(case: dict[str, str], account: dict[str, Any]) -> dict[str, Any]:
    payload = _json_field(case, "login_payload")
    rendered = _replace_placeholders(
        payload,
        {
            "{{dedicated_username}}": str(account["username"]),
            "{{dedicated_password}}": str(account["password"]),
        },
    )
    assert isinstance(rendered, dict)
    return rendered


def _expect_status(response: requests.Response, expected: str, action: str) -> None:
    expected = expected.strip()
    if expected.endswith("xx") and len(expected) == 3 and expected[0].isdigit():
        lower = int(expected[0]) * 100
        upper = lower + 100
        assert lower <= response.status_code < upper, (
            f"{action} expected {expected}, got {response.status_code}: {response.text[:500]}"
        )
        return

    assert response.status_code == int(expected), (
        f"{action} expected {expected}, got {response.status_code}: {response.text[:500]}"
    )


def _json_response(response: requests.Response, expected: str, action: str) -> dict[str, Any]:
    _expect_status(response, expected, action)
    if not response.text:
        return {}
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict), f"{action} returned non-object JSON: {payload!r}"
    return payload


def _data(payload: dict[str, Any]) -> Any:
    return payload.get("data", payload)


def _object(payload: dict[str, Any], action: str, *preferred_keys: str) -> dict[str, Any]:
    data = _data(payload)
    containers = [payload]
    if isinstance(data, dict):
        containers.append(data)

    for key in preferred_keys:
        for container in containers:
            value = container.get(key)
            if isinstance(value, dict):
                return value

    if isinstance(data, dict):
        return data
    pytest.fail(f"{action} returned non-object data: {payload!r}")


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    def collect(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for key in (
                "items",
                "risks",
                "tasks",
                "meetings",
                "requirements",
                "milestones",
                "reports",
                "test_plans",
                "test_cases",
                "defects",
                "results",
                "projects",
                "data",
            ):
                nested = collect(value.get(key))
                if nested:
                    return nested
        return []

    return collect(payload)


def _candidate_objects(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [payload]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.append(data)

    for container in list(candidates):
        for key in (
            "project",
            "task",
            "milestone",
            "test_plan",
            "test_case",
            "defect",
            "report",
            "config",
            "group",
            "model_config",
        ):
            value = container.get(key)
            if isinstance(value, dict):
                candidates.append(value)
    return candidates


def _try_extract_id(payload: dict[str, Any], *preferred_keys: str) -> Any | None:
    for item in _candidate_objects(payload):
        for key in (*preferred_keys, "id", "report_id"):
            value = item.get(key)
            if value is not None:
                return value
    return None


def _extract_id(payload: dict[str, Any], *preferred_keys: str) -> Any:
    value = _try_extract_id(payload, *preferred_keys)
    if value is None:
        pytest.fail(f"Response does not contain an id field: {payload!r}")
    return value


def _decimal_text(value: Any) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.00")))


def _format_path(template: str, resource_id: Any, path_vars: dict[str, Any]) -> str:
    return template.format(id=resource_id, **path_vars)


def _cleanup_path(session: requests.Session, base_url: str, path: str) -> None:
    response = session.delete(f"{base_url}{path}", timeout=10)
    assert response.status_code in {200, 202, 204, 400, 404}, (
        f"cleanup {path} failed: {response.status_code} {response.text[:500]}"
    )


def _delete_config(base_url: str, config_key: str, environment: str) -> None:
    admin_session, _payload = csv_login_admin_from_csv(base_url)
    try:
        response = admin_session.delete(
            f"{base_url}/api/v1/configs/configs/{config_key}",
            params={"environment": environment, "hard_delete": True},
            timeout=10,
        )
        assert response.status_code in {200, 202, 204, 400, 404}, (
            f"cleanup config {config_key} failed: {response.status_code} {response.text[:500]}"
        )
    finally:
        admin_session.close()


def _delete_defect_request(
    session: requests.Session,
    base_url: str,
    resource_id: Any,
    _path_vars: dict[str, Any],
) -> requests.Response:
    response = session.delete(f"{base_url}/api/v1/defects/{resource_id}", timeout=10)
    if response.status_code != 422:
        return response

    status_response = session.patch(
        f"{base_url}/api/v1/defects/{resource_id}/status",
        json={"status": "REJECTED", "notes": "pytest cleanup: make auto-created defect deletable"},
        timeout=10,
    )
    assert status_response.status_code in {200, 202}, (
        f"prepare defect cleanup failed: {status_response.status_code} {status_response.text[:500]}"
    )
    return session.delete(f"{base_url}/api/v1/defects/{resource_id}", timeout=10)


def _login_case() -> dict[str, str]:
    assert LOGIN_CASES, f"No login case was loaded from {DATA_PATH}"
    return LOGIN_CASES[0]


def _login_and_apply_token(session: requests.Session, base_url: str, account: dict[str, Any]) -> dict[str, Any]:
    case = _login_case()
    payload = _render_login_payload(case, account)
    response = session.post(f"{base_url}/api/v1/auth/login", json=payload, timeout=10)
    body = _json_response(response, case["expected_login_status"], "login from business CRUD csv")
    token = body.get("access_token")
    assert token, f"login from business CRUD csv did not return access_token: {body!r}"
    assert body.get("refresh_token"), f"login from business CRUD csv did not return refresh_token: {body!r}"
    assert str(body.get("token_type", "")).lower() == "bearer"
    session.headers.update({"Authorization": f"Bearer {token}"})
    return body


def _create_test_plan_dependency(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
) -> int:
    suffix = path_vars["unique_suffix"]
    plan_name = f"{AUTO_PREFIX}_PLAN_DEP_{suffix}"
    payload = _json_response(
        session.post(
            f"{base_url}/api/v1/test-plans/",
            json={
                "project_id": PROJECT_ID,
                "plan_name": plan_name,
                "description": "pytest CSV dependency test plan",
                "test_type": "FUNCTIONAL",
                "test_strategy": "CSV dependency",
                "test_scope": "business CRUD CSV",
                "planned_start_date": "2026-12-01",
                "planned_end_date": "2026-12-31",
                "test_manager_id": ADMIN_USER_ID,
            },
            timeout=10,
        ),
        "200",
        "create dependency test plan",
    )
    plan_id = int(_extract_id(payload))
    live_cleanup_stack.add(lambda: _cleanup_path(session, base_url, f"/api/v1/test-plans/{plan_id}"))
    _set_context_value(replacements, path_vars, "plan_id", plan_id)
    return plan_id


def _create_test_case_dependency(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
) -> int:
    plan_id = _create_test_plan_dependency(session, base_url, live_cleanup_stack, replacements, path_vars)
    suffix = path_vars["unique_suffix"]
    case_title = f"{AUTO_PREFIX}_CASE_DEP_{suffix}"
    payload = _json_response(
        session.post(
            f"{base_url}/api/v1/test-cases/",
            json={
                "test_plan_id": plan_id,
                "case_title": case_title,
                "case_description": "pytest CSV dependency test case",
                "case_type": "FUNCTIONAL",
                "module": "pytest",
                "priority": "LOW",
                "complexity": "LOW",
                "automation_level": "MANUAL",
                "preconditions": "created by pytest",
                "test_steps": [{"step": 1, "action": "call API", "expected": "success"}],
                "expected_result": "success",
                "test_data": {"source": "pytest"},
                "tags": [AUTO_PREFIX, "csv-dependency"],
            },
            timeout=10,
        ),
        "200",
        "create dependency test case",
    )
    case_id = int(_extract_id(payload))
    live_cleanup_stack.add(lambda: _cleanup_path(session, base_url, f"/api/v1/test-cases/{case_id}"))
    _set_context_value(replacements, path_vars, "case_id", case_id)
    return case_id


SearchParams = Callable[[dict[str, Any], Any, dict[str, Any]], dict[str, Any]]
PrepareCase = Callable[
    [requests.Session, str, LiveCleanupStack, dict[str, Any], dict[str, Any]],
    None,
]
DeleteRequest = Callable[[requests.Session, str, Any, dict[str, Any]], requests.Response]


@dataclass(frozen=True)
class IdCrudSpec:
    create_path: str
    read_path: str
    update_path: str | None
    delete_path: str
    list_path: str
    search_params: SearchParams
    object_keys: tuple[str, ...] = ()
    id_keys: tuple[str, ...] = ()
    identity_field: str | None = None
    update_assert_field: str | None = None
    prepare: PrepareCase | None = None
    delete_request: DeleteRequest | None = None


def _params(**values: Any) -> dict[str, Any]:
    return dict(values)


def _run_id_crud_case(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
) -> None:
    spec = ID_CRUD_SPECS[case["module"]]
    replacements, path_vars = _case_context(case)
    if spec.prepare is not None:
        spec.prepare(session, base_url, live_cleanup_stack, replacements, path_vars)

    if case["case_type"] == "normal":
        _run_id_crud_success(session, base_url, live_cleanup_stack, case, spec, replacements, path_vars)
        return
    if case["case_type"] == "abnormal":
        _run_id_create_abnormal(session, base_url, live_cleanup_stack, case, spec, replacements, path_vars)
        return

    pytest.fail(f"Unsupported CRUD case type: {case['case_type']}")


def _run_id_crud_success(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
    spec: IdCrudSpec,
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
) -> None:
    create_payload = _render_json_field(case, "create_payload", replacements)
    update_payload = _render_json_field(case, "update_payload", replacements)

    created_payload = _json_response(
        session.post(f"{base_url}{_format_path(spec.create_path, '', path_vars)}", json=create_payload, timeout=10),
        case["expected_create_status"],
        f"create {case['module']} from csv",
    )
    created = _object(created_payload, f"create {case['module']} from csv", *spec.object_keys)
    resource_id = _extract_id(created_payload, *spec.id_keys)
    cleanup = live_cleanup_stack.add(lambda: _cleanup_id_resource(session, base_url, spec, resource_id, path_vars))

    if (
        spec.identity_field
        and create_payload.get(spec.identity_field) is not None
        and created.get(spec.identity_field) is not None
    ):
        assert created.get(spec.identity_field) == create_payload[spec.identity_field]

    detail_payload = _json_response(
        session.get(f"{base_url}{_format_path(spec.read_path, resource_id, path_vars)}", timeout=10),
        case["expected_read_status"],
        f"read {case['module']} from csv",
    )
    detail = _object(detail_payload, f"read {case['module']} from csv", *spec.object_keys)
    if detail.get("id") is not None:
        assert str(detail["id"]) == str(resource_id)
    if spec.identity_field and detail.get(spec.identity_field) is not None:
        assert detail[spec.identity_field] == create_payload[spec.identity_field]

    if spec.update_path is not None and case["expected_update_status"].strip():
        updated_payload = _json_response(
            session.put(
                f"{base_url}{_format_path(spec.update_path, resource_id, path_vars)}",
                json=update_payload,
                timeout=10,
            ),
            case["expected_update_status"],
            f"update {case['module']} from csv",
        )
        updated = _object(updated_payload, f"update {case['module']} from csv", *spec.object_keys)
        update_field = spec.update_assert_field or spec.identity_field
        if update_field and update_field in update_payload and updated.get(update_field) is not None:
            assert updated[update_field] == update_payload[update_field]

    listed_payload = _json_response(
        session.get(
            f"{base_url}{_format_path(spec.list_path, resource_id, path_vars)}",
            params=spec.search_params(create_payload, resource_id, path_vars),
            timeout=10,
        ),
        case["expected_read_status"],
        f"search {case['module']} from csv",
    )
    assert any(
        str(item.get("id") or item.get("report_id")) == str(resource_id) for item in _items(listed_payload)
    ), f"created {case['module']} {resource_id!r} was not found in list response: {listed_payload!r}"

    delete_response = _send_delete(session, base_url, spec, resource_id, path_vars)
    _expect_status(delete_response, case["expected_delete_status"], f"delete {case['module']} from csv")
    live_cleanup_stack.discard(cleanup)

    deleted_get = session.get(f"{base_url}{_format_path(spec.read_path, resource_id, path_vars)}", timeout=10)
    _expect_status(deleted_get, case["expected_deleted_read_status"], f"read deleted {case['module']} from csv")


def _run_id_create_abnormal(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
    spec: IdCrudSpec,
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
) -> None:
    create_payload = _render_json_field(case, "create_payload", replacements)
    response = session.post(f"{base_url}{_format_path(spec.create_path, '', path_vars)}", json=create_payload, timeout=10)
    if response.status_code < 400 and response.text:
        try:
            created_payload = response.json()
        except ValueError:
            created_payload = {}
        if isinstance(created_payload, dict):
            resource_id = _try_extract_id(created_payload, *spec.id_keys)
            if resource_id is not None:
                _cleanup_id_resource(session, base_url, spec, resource_id, path_vars)
    _expect_status(response, case["expected_create_status"], f"create invalid {case['module']} from csv")


def _send_delete(
    session: requests.Session,
    base_url: str,
    spec: IdCrudSpec,
    resource_id: Any,
    path_vars: dict[str, Any],
) -> requests.Response:
    if spec.delete_request is not None:
        return spec.delete_request(session, base_url, resource_id, path_vars)
    return session.delete(f"{base_url}{_format_path(spec.delete_path, resource_id, path_vars)}", timeout=10)


def _cleanup_id_resource(
    session: requests.Session,
    base_url: str,
    spec: IdCrudSpec,
    resource_id: Any,
    path_vars: dict[str, Any],
) -> None:
    response = _send_delete(session, base_url, spec, resource_id, path_vars)
    assert response.status_code in {200, 202, 204, 400, 404}, (
        f"cleanup {spec.delete_path}/{resource_id} failed: {response.status_code} {response.text[:500]}"
    )


def _run_config_case(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
) -> None:
    replacements, _path_vars = _case_context(case)
    if case["case_type"] == "normal":
        _run_config_crud_success(session, base_url, live_cleanup_stack, case, replacements)
        return
    if case["case_type"] == "abnormal":
        _run_config_create_abnormal(session, base_url, live_cleanup_stack, case, replacements)
        return
    pytest.fail(f"Unsupported CRUD case type: {case['case_type']}")


def _run_config_crud_success(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
    replacements: dict[str, Any],
) -> None:
    create_payload = _render_json_field(case, "create_payload", replacements)
    update_payload = _render_json_field(case, "update_payload", replacements)
    config_key = str(create_payload["config_key"])
    environment = str(create_payload.get("environment", "test"))
    cleanup = live_cleanup_stack.add(lambda: _delete_config(base_url, config_key, environment))

    created = _object(
        _json_response(
            session.post(f"{base_url}/api/v1/configs/configs", json=create_payload, timeout=10),
            case["expected_create_status"],
            "create config from csv",
        ),
        "create config from csv",
    )
    assert created["config_key"] == config_key
    assert created["config_value"] == create_payload["config_value"]

    detail = _object(
        _json_response(
            session.get(
                f"{base_url}/api/v1/configs/configs/{config_key}",
                params={"environment": environment, "decrypt": False},
                timeout=10,
            ),
            case["expected_read_status"],
            "read config from csv",
        ),
        "read config from csv",
    )
    assert detail["config_key"] == config_key

    updated = _object(
        _json_response(
            session.put(
                f"{base_url}/api/v1/configs/configs/{config_key}",
                params={"environment": environment},
                json=update_payload,
                timeout=10,
            ),
            case["expected_update_status"],
            "update config from csv",
        ),
        "update config from csv",
    )
    assert updated["config_key"] == config_key
    assert updated["config_value"] == update_payload["config_value"]

    listed = _json_response(
        session.get(
            f"{base_url}/api/v1/configs/configs",
            params={"environment": environment, "search": config_key, "page": 1, "size": 20},
            timeout=10,
        ),
        case["expected_read_status"],
        "search config from csv",
    )
    assert any(item["config_key"] == config_key for item in _items(listed))

    delete_response = session.delete(
        f"{base_url}/api/v1/configs/configs/{config_key}",
        params={"environment": environment, "hard_delete": True},
        timeout=10,
    )
    _expect_status(delete_response, case["expected_delete_status"], "delete config from csv")
    live_cleanup_stack.discard(cleanup)

    deleted_get = session.get(
        f"{base_url}/api/v1/configs/configs/{config_key}",
        params={"environment": environment, "decrypt": False},
        timeout=10,
    )
    _expect_status(deleted_get, case["expected_deleted_read_status"], "read deleted config from csv")


def _run_config_create_abnormal(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
    replacements: dict[str, Any],
) -> None:
    create_payload = _render_json_field(case, "create_payload", replacements)
    config_key = create_payload.get("config_key")
    environment = str(create_payload.get("environment", "test"))
    if config_key:
        live_cleanup_stack.add(lambda: _delete_config(base_url, str(config_key), environment))

    response = session.post(f"{base_url}/api/v1/configs/configs", json=create_payload, timeout=10)
    _expect_status(response, case["expected_create_status"], "create invalid config from csv")


def _run_config_group_case(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
) -> None:
    replacements, _path_vars = _case_context(case)
    if case["case_type"] == "normal":
        _run_config_group_crud_success(session, base_url, live_cleanup_stack, case, replacements)
        return
    if case["case_type"] == "abnormal":
        create_payload = _render_json_field(case, "create_payload", replacements)
        response = session.post(f"{base_url}/api/v1/configs/groups", json=create_payload, timeout=10)
        if response.status_code < 400 and response.text:
            payload = response.json()
            group_id = _try_extract_id(payload)
            if group_id is not None:
                _cleanup_path(session, base_url, f"/api/v1/configs/groups/{group_id}")
        _expect_status(response, case["expected_create_status"], "create invalid config group from csv")
        return
    pytest.fail(f"Unsupported CRUD case type: {case['case_type']}")


def _run_config_group_crud_success(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
    replacements: dict[str, Any],
) -> None:
    create_payload = _render_json_field(case, "create_payload", replacements)
    update_payload = _render_json_field(case, "update_payload", replacements)

    created = _object(
        _json_response(
            session.post(f"{base_url}/api/v1/configs/groups", json=create_payload, timeout=10),
            case["expected_create_status"],
            "create config group from csv",
        ),
        "create config group from csv",
    )
    group_id = int(_extract_id(created))
    cleanup = live_cleanup_stack.add(lambda: _cleanup_path(session, base_url, f"/api/v1/configs/groups/{group_id}"))
    assert created["group_code"] == create_payload["group_code"]
    assert created["group_name"] == create_payload["group_name"]

    listed = _json_response(
        session.get(f"{base_url}/api/v1/configs/groups", timeout=10),
        case["expected_read_status"],
        "list config groups from csv",
    )
    assert any(item["id"] == group_id and item["group_code"] == create_payload["group_code"] for item in _items(listed))

    updated = _object(
        _json_response(
            session.put(f"{base_url}/api/v1/configs/groups/{group_id}", json=update_payload, timeout=10),
            case["expected_update_status"],
            "update config group from csv",
        ),
        "update config group from csv",
    )
    assert updated["group_name"] == update_payload["group_name"]
    assert updated["color"] == update_payload["color"]

    delete_response = session.delete(f"{base_url}/api/v1/configs/groups/{group_id}", timeout=10)
    _expect_status(delete_response, case["expected_delete_status"], "delete config group from csv")
    live_cleanup_stack.discard(cleanup)

    after_delete = _json_response(
        session.get(f"{base_url}/api/v1/configs/groups", timeout=10),
        case["expected_deleted_read_status"],
        "list config groups after delete from csv",
    )
    assert not any(item["id"] == group_id for item in _items(after_delete))


def _run_task_case(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
) -> None:
    spec = ID_CRUD_SPECS["tasks"]
    replacements, path_vars = _case_context(case)
    if case["case_type"] == "abnormal":
        _run_id_create_abnormal(session, base_url, live_cleanup_stack, case, spec, replacements, path_vars)
        return

    create_payload = _render_json_field(case, "create_payload", replacements)
    update_payload = _render_json_field(case, "update_payload", replacements)
    patch_payload = update_payload.pop("__patch__", {})

    created_payload = _json_response(
        session.post(f"{base_url}/api/v1/tasks", json=create_payload, timeout=10),
        case["expected_create_status"],
        "create task from csv",
    )
    created = _object(created_payload, "create task from csv", "task")
    task_id = int(_extract_id(created_payload))
    cleanup = live_cleanup_stack.add(lambda: _cleanup_path(session, base_url, f"/api/v1/tasks/{task_id}"))
    assert created["task_name"] == create_payload["task_name"]

    detail = _json_response(
        session.get(f"{base_url}/api/v1/tasks/{task_id}", timeout=10),
        case["expected_read_status"],
        "read task from csv",
    )
    assert detail["task_name"] == create_payload["task_name"]

    updated = _object(
        _json_response(
            session.put(f"{base_url}/api/v1/tasks/{task_id}", json=update_payload, timeout=10),
            case["expected_update_status"],
            "update task from csv",
        ),
        "update task from csv",
        "task",
    )
    assert updated["task_name"] == update_payload["task_name"]
    assert _decimal_text(updated["estimated_hours"]) == _decimal_text(update_payload["estimated_hours"])

    if patch_payload:
        patched = _object(
            _json_response(
                session.patch(f"{base_url}/api/v1/tasks/{task_id}", json=patch_payload, timeout=10),
                case["expected_update_status"],
                "patch task from csv",
            ),
            "patch task from csv",
            "task",
        )
        assert patched["description"] == patch_payload["description"]

    listed = _json_response(
        session.get(
            f"{base_url}/api/v1/tasks",
            params={"project_id": PROJECT_ID, "search": create_payload["task_name"], "page": 1, "size": 20},
            timeout=10,
        ),
        case["expected_read_status"],
        "search task from csv",
    )
    assert any(item["id"] == task_id for item in _items(listed))

    delete_response = session.delete(f"{base_url}/api/v1/tasks/{task_id}", timeout=10)
    _expect_status(delete_response, case["expected_delete_status"], "delete task from csv")
    live_cleanup_stack.discard(cleanup)
    deleted_get = session.get(f"{base_url}/api/v1/tasks/{task_id}", timeout=10)
    _expect_status(deleted_get, case["expected_deleted_read_status"], "read deleted task from csv")


def _run_create_test_plan_prepare(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
) -> None:
    _create_test_plan_dependency(session, base_url, live_cleanup_stack, replacements, path_vars)


def _run_create_test_case_prepare(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    replacements: dict[str, Any],
    path_vars: dict[str, Any],
) -> None:
    _create_test_case_dependency(session, base_url, live_cleanup_stack, replacements, path_vars)


ID_CRUD_SPECS: dict[str, IdCrudSpec] = {
    "projects": IdCrudSpec(
        create_path="/api/v1/projects",
        read_path="/api/v1/projects/{id}",
        update_path="/api/v1/projects/{id}",
        delete_path="/api/v1/projects/{id}",
        list_path="/api/v1/projects",
        search_params=lambda payload, _rid, _vars: _params(search=payload["project_name"], page=1, size=20),
        object_keys=("project",),
        identity_field="project_name",
        update_assert_field="project_name",
    ),
    "risks": IdCrudSpec(
        create_path="/api/v1/risks/",
        read_path="/api/v1/risks/{id}",
        update_path="/api/v1/risks/{id}",
        delete_path="/api/v1/risks/{id}",
        list_path="/api/v1/risks/",
        search_params=lambda payload, _rid, _vars: _params(
            project_id=PROJECT_ID, search=payload["risk_name"], page=1, page_size=20
        ),
        identity_field="risk_name",
        update_assert_field="risk_name",
    ),
    "meetings": IdCrudSpec(
        create_path="/api/v1/meetings/",
        read_path="/api/v1/meetings/{id}",
        update_path="/api/v1/meetings/{id}",
        delete_path="/api/v1/meetings/{id}",
        list_path="/api/v1/meetings/",
        search_params=lambda payload, _rid, _vars: _params(keyword=payload["title"], page=1, page_size=20),
        identity_field="title",
        update_assert_field="title",
    ),
    "requirements": IdCrudSpec(
        create_path="/api/v1/requirements/",
        read_path="/api/v1/requirements/{id}",
        update_path="/api/v1/requirements/{id}",
        delete_path="/api/v1/requirements/{id}",
        list_path="/api/v1/requirements/",
        search_params=lambda payload, _rid, _vars: _params(
            project_id=PROJECT_ID, keyword=payload["title"], skip=0, limit=20
        ),
        identity_field="title",
        update_assert_field="title",
    ),
    "milestones": IdCrudSpec(
        create_path="/api/v1/milestones/{project_id}",
        read_path="/api/v1/milestones/detail/{id}",
        update_path="/api/v1/milestones/{id}",
        delete_path="/api/v1/milestones/{id}",
        list_path="/api/v1/milestones/{project_id}",
        search_params=lambda payload, _rid, _vars: _params(search=payload["milestone_name"], page=1, size=20),
        object_keys=("milestone",),
        identity_field="milestone_name",
        update_assert_field="milestone_name",
    ),
    "ai_model_configs": IdCrudSpec(
        create_path="/api/v1/ai-model-config/",
        read_path="/api/v1/ai-model-config/{id}",
        update_path="/api/v1/ai-model-config/{id}",
        delete_path="/api/v1/ai-model-config/{id}",
        list_path="/api/v1/ai-model-config/",
        search_params=lambda payload, _rid, _vars: _params(provider=payload["provider"], skip=0, limit=100),
        identity_field="model_name",
        update_assert_field="display_name",
    ),
    "test_plans": IdCrudSpec(
        create_path="/api/v1/test-plans/",
        read_path="/api/v1/test-plans/{id}",
        update_path="/api/v1/test-plans/{id}",
        delete_path="/api/v1/test-plans/{id}",
        list_path="/api/v1/test-plans/",
        search_params=lambda payload, _rid, _vars: _params(
            project_id=PROJECT_ID, search=payload["plan_name"], page=1, size=20
        ),
        identity_field="plan_name",
        update_assert_field="plan_name",
    ),
    "test_cases": IdCrudSpec(
        create_path="/api/v1/test-cases/",
        read_path="/api/v1/test-cases/{id}",
        update_path="/api/v1/test-cases/{id}",
        delete_path="/api/v1/test-cases/{id}",
        list_path="/api/v1/test-cases/",
        search_params=lambda payload, _rid, vars_: _params(
            test_plan_id=vars_["plan_id"], search=payload["case_title"], page=1, size=20
        ),
        identity_field="case_title",
        update_assert_field="case_title",
        prepare=_run_create_test_plan_prepare,
    ),
    "defects": IdCrudSpec(
        create_path="/api/v1/defects/",
        read_path="/api/v1/defects/{id}",
        update_path="/api/v1/defects/{id}",
        delete_path="/api/v1/defects/{id}",
        list_path="/api/v1/defects/",
        search_params=lambda payload, _rid, vars_: _params(
            test_case_id=vars_["case_id"], search=payload["title"], page=1, size=20
        ),
        identity_field="title",
        update_assert_field="title",
        prepare=_run_create_test_case_prepare,
        delete_request=_delete_defect_request,
    ),
    "test_reports": IdCrudSpec(
        create_path="/api/v1/test-reports/generate",
        read_path="/api/v1/test-reports/{id}",
        update_path=None,
        delete_path="/api/v1/test-reports/{id}",
        list_path="/api/v1/test-reports/",
        search_params=lambda payload, _rid, _vars: _params(
            project_id=PROJECT_ID, search=payload["report_name"], page=1, size=20
        ),
        id_keys=("report_id",),
        identity_field="report_name",
    ),
    "tasks": IdCrudSpec(
        create_path="/api/v1/tasks",
        read_path="/api/v1/tasks/{id}",
        update_path="/api/v1/tasks/{id}",
        delete_path="/api/v1/tasks/{id}",
        list_path="/api/v1/tasks",
        search_params=lambda payload, _rid, _vars: _params(
            project_id=PROJECT_ID, search=payload["task_name"], page=1, size=20
        ),
        identity_field="task_name",
        update_assert_field="task_name",
    ),
}


CRUD_RUNNERS: dict[str, Callable[[requests.Session, str, LiveCleanupStack, dict[str, str]], None]] = {
    **{module: _run_id_crud_case for module in ID_CRUD_SPECS},
    "configs": _run_config_case,
    "config_groups": _run_config_group_case,
    "tasks": _run_task_case,
}
REQUIRED_CRUD_MODULES = set(CRUD_RUNNERS)


@pytest.mark.contract
def test_business_crud_csv_data_includes_normal_and_abnormal_cases() -> None:
    assert LOGIN_CASES, f"No login case was loaded from {DATA_PATH}"
    for case in LOGIN_CASES:
        assert case["case_type"] == "normal"
        assert case["expected_login_status"] == "200"
        payload = _json_field(case, "login_payload")
        assert payload.get("username") == "{{dedicated_username}}"
        assert payload.get("password") == "{{dedicated_password}}"

    assert CRUD_CASES, f"No business CRUD cases were loaded from {DATA_PATH}"
    unsupported = {case["module"] for case in CRUD_CASES} - REQUIRED_CRUD_MODULES
    assert not unsupported, f"Business CRUD CSV has unsupported modules: {sorted(unsupported)}"

    normal_modules = {case["module"] for case in CRUD_CASES if case["case_type"] == "normal"}
    abnormal_modules = {case["module"] for case in CRUD_CASES if case["case_type"] == "abnormal"}
    assert REQUIRED_CRUD_MODULES <= normal_modules, (
        "Business CRUD CSV is missing normal cases for modules: "
        f"{sorted(REQUIRED_CRUD_MODULES - normal_modules)}"
    )
    assert REQUIRED_CRUD_MODULES <= abnormal_modules, (
        "Business CRUD CSV is missing abnormal cases for modules: "
        f"{sorted(REQUIRED_CRUD_MODULES - abnormal_modules)}"
    )

    seen_case_ids: set[str] = set()
    for case in CRUD_CASES:
        assert case["case_id"] not in seen_case_ids, f"Duplicate business CRUD case_id: {case['case_id']}"
        seen_case_ids.add(case["case_id"])
        assert case["case_type"] in {"normal", "abnormal"}
        assert case["expected_create_status"]
        _json_field(case, "create_payload")
        _json_field(case, "update_payload")
        if case["case_type"] == "normal":
            assert case["expected_read_status"]
            assert case["expected_delete_status"]
            assert case["expected_deleted_read_status"]
            if "update" in case["operation"] or "patch" in case["operation"]:
                assert case["expected_update_status"]
        if case["case_type"] == "abnormal":
            assert case["expected_create_status"].startswith("4")


@pytest.mark.live
@pytest.mark.api
@pytest.mark.business_crud
@pytest.mark.flaky(reruns=0)
@pytest.mark.parametrize("case", LOGIN_CASES, ids=_case_id)
def test_login_case_from_csv_returns_token(
    base_url: str,
    csv_dedicated_account: dict[str, Any],
    case: dict[str, str],
) -> None:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    try:
        payload = _render_login_payload(case, csv_dedicated_account)
        response = session.post(f"{base_url}/api/v1/auth/login", json=payload, timeout=10)
        body = _json_response(response, case["expected_login_status"], "login from business CRUD csv")
    finally:
        session.close()

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"].lower() == "bearer"


@pytest.mark.live
@pytest.mark.api
@pytest.mark.business_crud
@pytest.mark.flaky(reruns=0)
@pytest.mark.parametrize("case", CRUD_CASES, ids=_case_id)
def test_business_crud_case_from_csv(
    base_url: str,
    csv_dedicated_account: dict[str, Any],
    live_cleanup_stack: LiveCleanupStack,
    case: dict[str, str],
) -> None:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    live_cleanup_stack.add(session.close)
    _login_and_apply_token(session, base_url, csv_dedicated_account)

    runner = CRUD_RUNNERS.get(case["module"])
    assert runner is not None, f"Unsupported CRUD module: {case['module']}"
    runner(session, base_url, live_cleanup_stack, case)
