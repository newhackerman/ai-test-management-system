from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    CSV_TEST_ACCOUNT_DATA_PATH,
    CSV_TEST_ACCOUNT_REQUIRED_COLUMNS,
    csv_login_admin_from_csv,
    csv_login_dedicated_from_csv,
    csv_test_account_case,
    csv_test_account_json_field,
)


pytestmark = [pytest.mark.api, pytest.mark.coverage]


def _load_account_rows() -> list[dict[str, str]]:
    with Path(CSV_TEST_ACCOUNT_DATA_PATH).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = CSV_TEST_ACCOUNT_REQUIRED_COLUMNS - set(reader.fieldnames or [])
        assert not missing, f"CSV test account data missing columns: {sorted(missing)}"
        return list(reader)


@pytest.mark.contract
def test_test_account_csv_data_contract() -> None:
    rows = _load_account_rows()
    case_ids = {row["case_id"] for row in rows}

    assert {
        "admin_login_success",
        "dedicated_user_create",
        "dedicated_user_assign_role",
        "dedicated_user_login_success",
    } <= case_ids

    admin_payload = csv_test_account_json_field(csv_test_account_case("admin_login_success"), "body_json")
    assert admin_payload == {"username": "admin", "password": "Admin123!"}

    create_payload = csv_test_account_json_field(csv_test_account_case("dedicated_user_create"), "body_json")
    assert create_payload["username"].startswith("pytest_auto_dedicated_")
    assert create_payload["password"]
    assert create_payload["role_ids"] == [3]

    assign_payload = csv_test_account_json_field(csv_test_account_case("dedicated_user_assign_role"), "body_json")
    assert assign_payload["role_ids"] == [3]

    for row in rows:
        assert row["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert row["expected_status"]
        json.loads(row["params_json"] or "{}")
        json.loads(row["body_json"] or "{}")


@pytest.mark.live
@pytest.mark.flaky(reruns=0)
def test_admin_login_case_from_csv_returns_token(base_url: str) -> None:
    session, payload = csv_login_admin_from_csv(base_url)
    try:
        assert payload["access_token"]
        assert payload["refresh_token"]
        assert payload["token_type"].lower() == "bearer"
    finally:
        session.close()


@pytest.mark.live
@pytest.mark.business_crud
@pytest.mark.flaky(reruns=0)
def test_dedicated_user_creation_case_from_csv(csv_dedicated_account: dict[str, Any]) -> None:
    assert csv_dedicated_account["create_case_id"] == "dedicated_user_create"
    assert csv_dedicated_account["assign_case_id"] == "dedicated_user_assign_role"
    assert csv_dedicated_account["user_id"] > 0
    assert csv_dedicated_account["username"].startswith("pytest_auto_dedicated_")
    assert csv_dedicated_account["email"].endswith("@example.com")
    assert csv_dedicated_account["requested_role_ids"] == [3]
    assert 3 in csv_dedicated_account["role_ids"]
    assert "SUPER_ADMIN" in csv_dedicated_account["role_codes"]
    assert 200 <= csv_dedicated_account["assign_status_code"] < 300


@pytest.mark.live
@pytest.mark.flaky(reruns=0)
def test_dedicated_user_login_case_from_csv_returns_token(
    base_url: str,
    csv_dedicated_account: dict[str, Any],
) -> None:
    session, payload = csv_login_dedicated_from_csv(base_url, csv_dedicated_account)
    try:
        assert payload["access_token"]
        assert payload["refresh_token"]
        assert payload["token_type"].lower() == "bearer"
    finally:
        session.close()
