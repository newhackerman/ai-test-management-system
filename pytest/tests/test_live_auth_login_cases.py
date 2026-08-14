from __future__ import annotations

import uuid
from typing import Any

import pytest
import requests

from conftest import csv_create_dedicated_account_from_csv, csv_delete_dedicated_account_from_csv


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.security, pytest.mark.flaky(reruns=0)]


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def _login(session: requests.Session, base_url: str, payload: Any, *, raw: bool = False) -> requests.Response:
    if raw:
        return session.post(
            f"{base_url}/api/v1/auth/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    return session.post(f"{base_url}/api/v1/auth/login", json=payload, timeout=10)


def _assert_login_failed(response: requests.Response) -> None:
    assert response.status_code in {400, 401, 422}
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def _assert_login_failed_or_locked(response: requests.Response) -> None:
    assert response.status_code in {400, 401, 422, 423, 429}
    assert "access_token" not in response.text
    assert "refresh_token" not in response.text


def _render_login_test_data(value: Any, username: str, password: str) -> Any:
    if isinstance(value, str):
        return (
            value.replace("{{username_upper}}", username.upper())
            .replace("{{username}}", username)
            .replace("{{password}}", password)
        )
    if isinstance(value, list):
        return [_render_login_test_data(item, username, password) for item in value]
    if isinstance(value, dict):
        return {key: _render_login_test_data(item, username, password) for key, item in value.items()}
    return value


def test_login_with_correct_username_and_password_returns_tokens(
    base_url: str,
    auth_credentials: tuple[str, str],
) -> None:
    username, password = auth_credentials

    with _session() as session:
        response = _login(session, base_url, {"username": username, "password": password})

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"].lower() == "bearer"


def test_login_with_wrong_username_and_correct_password_is_rejected(
    base_url: str,
    auth_credentials: tuple[str, str],
) -> None:
    _username, password = auth_credentials

    with _session() as session:
        response = _login(session, base_url, {"username": f"not_exist_{uuid.uuid4().hex}", "password": password})

    _assert_login_failed(response)


def test_login_with_wrong_username_and_wrong_password_is_rejected(base_url: str) -> None:
    with _session() as session:
        response = _login(
            session,
            base_url,
            {
                "username": f"not_exist_{uuid.uuid4().hex}",
                "password": f"Wrong_{uuid.uuid4().hex}!",
            },
        )

    _assert_login_failed(response)


def test_login_with_correct_username_and_wrong_password_is_rejected_without_locking_account(
    base_url: str,
    auth_credentials: tuple[str, str],
) -> None:
    username, password = auth_credentials

    with _session() as session:
        failed_response = _login(session, base_url, {"username": username, "password": f"Wrong_{uuid.uuid4().hex}!"})
        recovery_response = _login(session, base_url, {"username": username, "password": password})

    _assert_login_failed(failed_response)
    assert recovery_response.status_code == 200
    assert recovery_response.json()["access_token"]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"username": "", "password": "{{password}}"}, id="empty_username"),
        pytest.param({"username": "{{username}}", "password": ""}, id="empty_password"),
        pytest.param({"username": "", "password": ""}, id="empty_username_and_password"),
        pytest.param({"password": "{{password}}"}, id="missing_username"),
        pytest.param({"username": "{{username}}"}, id="missing_password"),
        pytest.param({}, id="missing_body_fields"),
        pytest.param({"username": None, "password": "{{password}}"}, id="null_username"),
        pytest.param({"username": "{{username}}", "password": None}, id="null_password"),
        pytest.param({"username": 12345, "password": "{{password}}"}, id="numeric_username"),
        pytest.param({"username": "{{username}}", "password": 12345}, id="numeric_password"),
    ],
)
def test_login_rejects_empty_missing_null_or_wrong_type_fields(
    base_url: str,
    auth_credentials: tuple[str, str],
    payload: dict[str, Any],
) -> None:
    username, password = auth_credentials
    rendered_payload = _render_login_test_data(payload, username, password)

    with _session() as session:
        response = _login(session, base_url, rendered_payload)

    _assert_login_failed(response)


@pytest.mark.parametrize(
    "username_template",
    [
        pytest.param("' OR '1'='1", id="sql_injection_basic"),
        pytest.param("{{username}}' --", id="sql_comment"),
        pytest.param("{{username}}; DROP TABLE users; --", id="sql_drop_table"),
        pytest.param("\" OR \"1\"=\"1", id="sql_double_quote"),
        pytest.param("<script>alert(1)</script>", id="xss_payload"),
        pytest.param("<img src=x onerror=alert(1)>", id="xss_img_onerror"),
        pytest.param(" {{username}} ", id="leading_trailing_spaces"),
        pytest.param("{{username}}\t", id="tab_suffix"),
        pytest.param("{{username}}\n", id="newline_suffix"),
        pytest.param("{{username}}\U0001f600", id="emoji_suffix"),
        pytest.param("\u6d4b\u8bd5\u7528\u6237", id="unicode_username"),
        pytest.param("not_{{username}}@example.com", id="email_format_username"),
        pytest.param("!@#$%^&*()_+-=[]{}|;':,.<>/?", id="special_chars_username"),
        pytest.param("a" * 512, id="overlong_username"),
    ],
)
def test_login_rejects_malicious_or_boundary_usernames(
    base_url: str,
    auth_credentials: tuple[str, str],
    username_template: str,
) -> None:
    username, password = auth_credentials
    rendered_username = _render_login_test_data(username_template, username, password)

    with _session() as session:
        response = _login(session, base_url, {"username": rendered_username, "password": password})

    _assert_login_failed(response)


@pytest.mark.parametrize(
    "password_template",
    [
        pytest.param("' OR '1'='1", id="sql_injection_password"),
        pytest.param("anything' --", id="sql_comment_password"),
        pytest.param("<script>alert(1)</script>", id="xss_password"),
        pytest.param("<img src=x onerror=alert(1)>", id="xss_img_password"),
        pytest.param(" \u5bc6\u7801 ", id="unicode_password_with_spaces"),
        pytest.param("!@#$%^&*()_+-=[]{}|;':,.<>/?", id="special_chars_password"),
        pytest.param("{{password}}\t", id="tab_suffix_password"),
        pytest.param("{{password}}\n", id="newline_suffix_password"),
    ],
)
def test_login_rejects_malicious_or_special_passwords_for_unknown_user(
    base_url: str,
    auth_credentials: tuple[str, str],
    password_template: str,
) -> None:
    username, password = auth_credentials
    rendered_password = _render_login_test_data(password_template, username, password)

    with _session() as session:
        response = _login(session, base_url, {"username": f"not_exist_{uuid.uuid4().hex}", "password": rendered_password})

    _assert_login_failed(response)


def test_login_rejects_overlong_password(base_url: str, auth_credentials: tuple[str, str]) -> None:
    username = auth_credentials[0]

    with _session() as session:
        response = _login(session, base_url, {"username": username, "password": "P" * 2048})

    _assert_login_failed(response)


def test_login_rejects_malformed_json_body(base_url: str) -> None:
    with _session() as session:
        response = _login(session, base_url, "{not-valid-json", raw=True)

    assert response.status_code == 422
    assert "access_token" not in response.text


@pytest.mark.parametrize("remember_me", [True, False])
def test_login_accepts_remember_me_boolean(
    base_url: str,
    auth_credentials: tuple[str, str],
    remember_me: bool,
) -> None:
    username, password = auth_credentials

    with _session() as session:
        response = _login(session, base_url, {"username": username, "password": password, "remember_me": remember_me})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_token_with_valid_refresh_token_returns_new_access_token(
    base_url: str,
    auth_credentials: tuple[str, str],
) -> None:
    username, password = auth_credentials

    with _session() as session:
        login_response = _login(session, base_url, {"username": username, "password": password})
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        refresh_response = session.post(
            f"{base_url}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10,
        )

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]


def test_refresh_token_rejects_missing_or_invalid_token(base_url: str) -> None:
    with _session() as session:
        missing_response = session.post(f"{base_url}/api/v1/auth/refresh", json={}, timeout=10)
        invalid_response = session.post(
            f"{base_url}/api/v1/auth/refresh",
            json={"refresh_token": f"invalid-{uuid.uuid4().hex}"},
            timeout=10,
        )

    assert missing_response.status_code in {400, 422}
    assert invalid_response.status_code == 401


def test_logout_with_valid_access_token_succeeds(base_url: str, auth_credentials: tuple[str, str]) -> None:
    username, password = auth_credentials

    with _session() as session:
        login_response = _login(session, base_url, {"username": username, "password": password})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        logout_response = session.post(
            f"{base_url}/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

    assert logout_response.status_code == 200


def test_logout_without_token_is_rejected(base_url: str) -> None:
    with _session() as session:
        response = session.post(f"{base_url}/api/v1/auth/logout", timeout=10)

    assert response.status_code in {401, 403}


def test_login_lockout_after_more_than_nine_failures_requires_dedicated_account(base_url: str) -> None:
    account = csv_create_dedicated_account_from_csv(base_url)
    username = str(account["username"])
    password = str(account["password"])

    try:
        wrong_password = f"Wrong_{uuid.uuid4().hex}!"
        with _session() as session:
            for _ in range(10):
                response = _login(session, base_url, {"username": username, "password": wrong_password})
                _assert_login_failed_or_locked(response)

            locked_response = _login(session, base_url, {"username": username, "password": password})

        assert locked_response.status_code in {401, 403, 423, 429}
        assert "access_token" not in locked_response.text
    finally:
        csv_delete_dedicated_account_from_csv(base_url, account)
