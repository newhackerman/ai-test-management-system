from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "test_cases" / "openapi_snapshot.json"
METHODS = {"get", "post", "put", "patch", "delete"}
BODY_METHODS = {"post", "put", "patch"}
SKIP_LIVE_PATH_PARTS = ("websocket", "/ws/", "/stream")


def _load_snapshot() -> dict:
    if not SNAPSHOT_PATH.exists():
        pytest.skip(f"OpenAPI snapshot does not exist: {SNAPSHOT_PATH}", allow_module_level=True)
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


SCHEMA = _load_snapshot()


def _iter_operations():
    for path, operations in sorted(SCHEMA.get("paths", {}).items()):
        for method, operation in sorted(operations.items()):
            if method in METHODS and isinstance(operation, dict):
                yield method, path, operation


def _resolve_schema(schema: dict) -> dict:
    if "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        return SCHEMA.get("components", {}).get("schemas", {}).get(ref_name, {})
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            if option.get("type") != "null":
                return _resolve_schema(option)
    if "items" in schema:
        return _resolve_schema(schema["items"])
    return schema


def _invalid_value_for_schema(schema: dict) -> str | None:
    resolved = _resolve_schema(schema)
    if "enum" in resolved:
        return "__invalid_enum__"
    value_type = resolved.get("type")
    value_format = resolved.get("format")
    if value_type in {"integer", "number"}:
        return "not-a-number"
    if value_type == "boolean":
        return "not-a-bool"
    if value_format in {"date", "date-time"}:
        return "not-a-date"
    return None


def _sample_for_param(name: str) -> str:
    lowered = name.lower()
    if "id" in lowered or lowered.endswith("_index"):
        return "999999"
    if "email" in lowered:
        return quote("pytest@example.com")
    if "date" in lowered:
        return "2026-01-01"
    if "format" in lowered:
        return "json"
    if "code" in lowered:
        return "PYTEST"
    return "pytest"


def _sample_path(path: str, override: tuple[str, str] | None = None) -> str:
    rendered = path
    while "{" in rendered and "}" in rendered:
        start = rendered.index("{")
        end = rendered.index("}", start)
        raw = rendered[start + 1 : end]
        name = raw.split(":")[0]
        value = override[1] if override and override[0] == name else _sample_for_param(name)
        rendered = rendered[:start] + value + rendered[end + 1 :]
    return rendered


def _skip_probe(path: str) -> bool:
    lowered = path.lower()
    return any(part in lowered for part in SKIP_LIVE_PATH_PARTS)


def _query_cases() -> list[dict]:
    cases = []
    for method, path, operation in _iter_operations():
        if method != "get" or _skip_probe(path):
            continue
        for parameter in operation.get("parameters", []):
            if parameter.get("in") != "query":
                continue
            invalid_value = _invalid_value_for_schema(parameter.get("schema", {}))
            if invalid_value is None:
                continue
            cases.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "param": parameter["name"],
                    "value": invalid_value,
                }
            )
            break
    return cases


def _path_cases() -> list[dict]:
    cases = []
    for method, path, operation in _iter_operations():
        if _skip_probe(path):
            continue
        for parameter in operation.get("parameters", []):
            if parameter.get("in") != "path":
                continue
            resolved = _resolve_schema(parameter.get("schema", {}))
            if resolved.get("type") == "integer" or "id" in parameter["name"].lower():
                cases.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "param": parameter["name"],
                        "value": "not-an-int",
                    }
                )
                break
    return cases


def _body_cases() -> list[dict]:
    cases = []
    for method, path, operation in _iter_operations():
        if method not in BODY_METHODS or _skip_probe(path):
            continue
        content = operation.get("requestBody", {}).get("content", {})
        if "application/json" not in content:
            continue
        cases.append({"method": method.upper(), "path": path})
    return cases


QUERY_CASES = _query_cases()
PATH_CASES = _path_cases()
BODY_CASES = _body_cases()


def _id(case: dict) -> str:
    suffix = f" {case.get('param', '')}".strip()
    return f"{case['method']} {case['path']} {suffix}".strip()


@pytest.mark.parametrize("case", QUERY_CASES, ids=_id)
def test_invalid_query_parameter_returns_4xx_not_500(
    live_session: requests.Session,
    base_url: str,
    case: dict,
) -> None:
    response = live_session.get(
        f"{base_url}{_sample_path(case['path'])}",
        params={case["param"]: case["value"]},
        timeout=10,
    )

    assert 400 <= response.status_code < 500, f"Expected 4xx for invalid query param, got {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize("case", PATH_CASES, ids=_id)
def test_invalid_path_parameter_returns_4xx_not_500(
    live_session: requests.Session,
    base_url: str,
    case: dict,
) -> None:
    url = f"{base_url}{_sample_path(case['path'], (case['param'], case['value']))}"
    response = live_session.request(case["method"], url, timeout=10)

    assert 400 <= response.status_code < 500, f"Expected 4xx for invalid path param, got {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize("case", BODY_CASES, ids=_id)
def test_malformed_json_body_returns_4xx_not_500(
    live_session: requests.Session,
    base_url: str,
    case: dict,
) -> None:
    response = live_session.request(
        case["method"],
        f"{base_url}{_sample_path(case['path'])}",
        data="{not-valid-json",
        headers={"Content-Type": "application/json"},
        timeout=10,
    )

    assert 400 <= response.status_code < 500, f"Expected 4xx for malformed JSON body, got {response.status_code}: {response.text[:300]}"
