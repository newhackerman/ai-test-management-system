from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
import requests

from conftest import csv_login_dedicated_from_csv


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.coverage]

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "test_cases" / "feature_probe_case_data.csv"
SNAPSHOT_PATH = ROOT / "test_cases" / "openapi_snapshot.json"
MISSING_KEY = f"PYTEST_AUTO_MISSING_{uuid.uuid4().hex[:10]}"
REQUIRED_COLUMNS = {
    "case_id",
    "feature",
    "case_type",
    "method",
    "path",
    "auth_required",
    "params_json",
    "body_json",
    "expected_status",
    "description",
    "covered_tags",
}
METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}


def _load_cases() -> list[dict[str, str]]:
    if not DATA_PATH.exists():
        pytest.fail(f"Feature probe case data does not exist: {DATA_PATH}", pytrace=False)

    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            pytest.fail(f"Feature probe case data missing columns: {sorted(missing)}")
        return list(reader)


def _load_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        pytest.fail(f"OpenAPI snapshot does not exist: {SNAPSHOT_PATH}", pytrace=False)
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


CASES = _load_cases()
SNAPSHOT = _load_snapshot()


def _case_id(case: dict[str, str]) -> str:
    return f"{case['feature']} {case['case_type']} {case['method']} {case['path']}"


def _json_field(case: dict[str, str], column: str) -> Any:
    raw = (case.get(column) or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{case['case_id']} has invalid JSON in {column}: {exc}")


def _replace_placeholders(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        rendered = value
        for placeholder, replacement in replacements.items():
            rendered = rendered.replace(placeholder, replacement)
        return rendered
    if isinstance(value, list):
        return [_replace_placeholders(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_placeholders(item, replacements) for key, item in value.items()}
    return value


def _replacements(account: dict[str, Any]) -> dict[str, str]:
    return {
        "{{dedicated_username}}": str(account["username"]),
        "{{dedicated_password}}": str(account["password"]),
        "{{missing_key}}": MISSING_KEY,
        "{{unique}}": uuid.uuid4().hex[:10],
    }


def _expect_status(response: requests.Response, expected: str, case: dict[str, str]) -> None:
    expected = expected.strip()
    if expected.endswith("xx") and len(expected) == 3 and expected[0].isdigit():
        lower = int(expected[0]) * 100
        upper = lower + 100
        assert lower <= response.status_code < upper, (
            f"{case['case_id']} expected {expected}, got {response.status_code}: {response.text[:500]}"
        )
        return

    assert response.status_code == int(expected), (
        f"{case['case_id']} expected {expected}, got {response.status_code}: {response.text[:500]}"
    )


def _operation_paths() -> set[tuple[str, str]]:
    paths: set[tuple[str, str]] = set()
    for path, operations in SNAPSHOT.get("paths", {}).items():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"} and isinstance(operation, dict):
                paths.add((method.upper(), path))
    return paths


def _path_matches(template: str, concrete: str) -> bool:
    template_parts = template.strip("/").split("/")
    concrete_parts = concrete.strip("/").split("/")
    if len(template_parts) != len(concrete_parts):
        return False
    return all(part.startswith("{") and part.endswith("}") or part == value for part, value in zip(template_parts, concrete_parts))


def _case_path_exists(case: dict[str, str], operation_paths: set[tuple[str, str]]) -> bool:
    method = case["method"].upper()
    path = case["path"]
    return any(candidate_method == method and _path_matches(candidate_path, path) for candidate_method, candidate_path in operation_paths)


def _openapi_tags() -> set[str]:
    tags: set[str] = set()
    for operations in SNAPSHOT.get("paths", {}).values():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or not isinstance(operation, dict):
                continue
            for tag in operation.get("tags") or []:
                tags.add(str(tag))
    return tags


def _covered_tags() -> set[str]:
    tags: set[str] = set()
    for case in CASES:
        tags.update(tag.strip() for tag in case["covered_tags"].split(";") if tag.strip())
    return tags


@pytest.mark.contract
def test_feature_probe_csv_data_covers_every_openapi_tag() -> None:
    missing_tags = sorted(_openapi_tags() - _covered_tags())
    assert not missing_tags, "Feature probe CSV does not cover OpenAPI tags:\n" + "\n".join(missing_tags)


@pytest.mark.contract
def test_feature_probe_csv_data_has_normal_and_abnormal_cases_per_feature() -> None:
    assert CASES, f"No feature probe cases were loaded from {DATA_PATH}"
    by_feature: dict[str, set[str]] = {}
    operation_paths = _operation_paths()

    for case in CASES:
        by_feature.setdefault(case["feature"], set()).add(case["case_type"])
        assert case["case_type"] in {"normal", "abnormal"}
        assert case["method"].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert case["auth_required"].lower() in {"true", "false"}
        assert case["expected_status"]
        assert case["covered_tags"]
        assert _case_path_exists(case, operation_paths), f"{case['case_id']} path is not in OpenAPI: {case['method']} {case['path']}"
        _json_field(case, "params_json")
        _json_field(case, "body_json")

    missing_pairs = {
        feature: {"normal", "abnormal"} - case_types
        for feature, case_types in by_feature.items()
        if {"normal", "abnormal"} - case_types
    }
    assert not missing_pairs, f"Each feature must have normal and abnormal probes: {missing_pairs}"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
@pytest.mark.flaky(reruns=0)
def test_feature_probe_case_from_csv(
    base_url: str,
    csv_dedicated_account: dict[str, Any],
    case: dict[str, str],
) -> None:
    replacements = _replacements(csv_dedicated_account)
    params = _replace_placeholders(_json_field(case, "params_json"), replacements)
    body = _replace_placeholders(_json_field(case, "body_json"), replacements)
    path = _replace_placeholders(case["path"], replacements)

    if case["auth_required"].lower() == "true":
        session, _login_payload = csv_login_dedicated_from_csv(base_url, csv_dedicated_account)
    else:
        session = requests.Session()
        session.headers.update({"Accept": "application/json"})
    try:
        kwargs: dict[str, Any] = {"params": params, "timeout": 15}
        if case["method"].upper() in METHODS_WITH_BODY:
            kwargs["json"] = body
        response = session.request(case["method"].upper(), f"{base_url}{path}", **kwargs)
    finally:
        session.close()

    _expect_status(response, case["expected_status"], case)
    if case["case_type"] == "normal" and response.text and response.status_code != 204:
        assert response.headers.get("content-type", "").startswith("application/json"), (
            f"{case['case_id']} returned non-JSON success: {response.headers.get('content-type')}"
        )
