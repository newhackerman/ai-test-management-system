from __future__ import annotations

import csv
import importlib
import json
import os
import sys
import uuid
from contextvars import ContextVar
from collections.abc import Callable
from pathlib import Path
from typing import Any, Iterator

import pytest

try:
    import allure
except Exception:  # pragma: no cover - allure is optional outside report runs.
    allure = None  # type: ignore[assignment]

try:
    import requests
except Exception:  # pragma: no cover - requests is installed in the test env.
    requests = None  # type: ignore[assignment]


DEFAULT_TARGET_ROOT = Path(r"D:\pythonTtest\ai-test-management-system")
CSV_TEST_ACCOUNT_DATA_PATH = Path(__file__).resolve().parent / "test_cases" / "test_account_case_data.csv"
CSV_TEST_ACCOUNT_REQUIRED_COLUMNS = {
    "case_id",
    "operation",
    "method",
    "path",
    "auth_context",
    "params_json",
    "body_json",
    "expected_status",
    "description",
}
_CURRENT_TEST_NODEID: ContextVar[str | None] = ContextVar("_CURRENT_TEST_NODEID", default=None)
_CURRENT_HTTP_INDEX: ContextVar[int] = ContextVar("_CURRENT_HTTP_INDEX", default=0)
_ORIGINAL_REQUEST = requests.sessions.Session.request if requests is not None else None


def _truncate_text(value: str, limit: int = 20000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n... truncated, original length={len(value)}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return _truncate_text(value.decode("utf-8", errors="replace"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return repr(value)


def _attach_allure_json(name: str, payload: dict[str, Any]) -> None:
    if allure is None:
        return
    allure.attach(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def _install_allure_http_recorder() -> None:
    if requests is None or _ORIGINAL_REQUEST is None:
        return
    if getattr(requests.sessions.Session.request, "_aitms_allure_wrapped", False):
        return

    def recorded_request(self, method: str, url: str, **kwargs):
        response = None
        error: BaseException | None = None
        try:
            response = _ORIGINAL_REQUEST(self, method, url, **kwargs)
            return response
        except BaseException as exc:
            error = exc
            raise
        finally:
            if allure is not None and _CURRENT_TEST_NODEID.get():
                index = _CURRENT_HTTP_INDEX.get() + 1
                _CURRENT_HTTP_INDEX.set(index)
                request_payload = {
                    "test": _CURRENT_TEST_NODEID.get(),
                    "method": method.upper(),
                    "url": url,
                    "params": kwargs.get("params"),
                    "json": kwargs.get("json"),
                    "data": kwargs.get("data"),
                    "headers": dict(kwargs.get("headers") or {}),
                    "timeout": kwargs.get("timeout"),
                }
                if response is not None:
                    response_payload: dict[str, Any] = {
                        "status_code": response.status_code,
                        "reason": response.reason,
                        "url": response.url,
                        "headers": dict(response.headers),
                        "elapsed_seconds": response.elapsed.total_seconds(),
                        "body": _truncate_text(response.text),
                    }
                else:
                    response_payload = {
                        "error_type": type(error).__name__ if error else None,
                        "error": str(error) if error else None,
                    }
                _attach_allure_json(
                    f"HTTP {index:03d} {method.upper()} {url}",
                    {"request": request_payload, "response": response_payload},
                )

    recorded_request._aitms_allure_wrapped = True  # type: ignore[attr-defined]
    requests.sessions.Session.request = recorded_request


_install_allure_http_recorder()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "aitms_allure_timestamp_format",
        default="yyyyMMdd_HHmmss",
        help="PowerShell Get-Date format used by scripts/run_allure_tests.ps1.",
    )
    parser.addini(
        "aitms_allure_results_template",
        default="reports/allure-results/{timestamp}",
        help="Allure results directory template relative to pytest.ini.",
    )
    parser.addini(
        "aitms_allure_report_template",
        default="reports/allure-report/{timestamp}",
        help="Allure report directory template relative to pytest.ini.",
    )
    parser.addoption(
        "--aitms-target-root",
        action="store",
        default=os.getenv("AITMS_TARGET_ROOT", str(DEFAULT_TARGET_ROOT)),
        help="AI test management system project root.",
    )
    parser.addoption(
        "--aitms-base-url",
        action="store",
        default=os.getenv("AITMS_BASE_URL", "http://127.0.0.1:8000"),
        help="Running backend base URL for tests marked live.",
    )
    parser.addoption(
        "--aitms-frontend-url",
        action="store",
        default=os.getenv("AITMS_FRONTEND_URL", "http://localhost:3000"),
        help="Running frontend URL for tests marked e2e.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    regression_mark = pytest.mark.regression

    for item in items:
        if item.get_closest_marker("smoke"):
            item.user_properties.append(("测试分类", "冒烟测试"))
            continue
        item.add_marker(regression_mark)
        item.user_properties.append(("测试分类", "回归测试"))

    # 预导入后端 src.main：import 耗时（几百个路由 + pydantic schema 生成）
    # 超过 per-test 的 --timeout=10，在 collection 阶段（不受 per-test timeout 限制）
    # 提前完成，后续 fixture 触发时 sys.modules 已缓存，瞬间返回。
    _preload_backend_app(config)


def _preload_backend_app(config: pytest.Config) -> None:
    import importlib

    if "src.main" in sys.modules:
        return  # 已加载，跳过

    try:
        root = Path(config.getoption("--aitms-target-root")).resolve()
    except Exception:
        return  # option 不存在时静默跳过

    backend_dir = root / "backend"
    if not backend_dir.exists():
        return

    backend_path = str(backend_dir)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault("CONFIG_ENCRYPTION_KEY", "pytest-local-config-key")
    os.environ.setdefault("LOG_LEVEL", "WARNING")

    previous_cwd = Path.cwd()
    try:
        os.chdir(backend_dir)
        importlib.import_module("src.main")
    except Exception:
        # 预导入失败不阻塞 collection，让真正的 fixture 抛出可读错误
        pass
    finally:
        os.chdir(previous_cwd)


def pytest_runtest_setup(item: pytest.Item) -> None:
    _CURRENT_TEST_NODEID.set(item.nodeid)
    _CURRENT_HTTP_INDEX.set(0)
    if allure is not None and hasattr(item, "callspec"):
        params = getattr(item.callspec, "params", {})
        if params:
            _attach_allure_json("Pytest parameters", {"parameters": params})
            for name, value in params.items():
                allure.dynamic.parameter(str(name), repr(_json_safe(value)))


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    _CURRENT_TEST_NODEID.set(None)
    _CURRENT_HTTP_INDEX.set(0)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if allure is None or report.passed or call.excinfo is None:
        return

    _attach_allure_json(
        "Assertion / failure details",
        {
            "test": item.nodeid,
            "phase": report.when,
            "exception_type": call.excinfo.typename,
            "exception_message": str(call.excinfo.value),
            "longrepr": str(report.longrepr),
        },
    )


@pytest.fixture(scope="session")
def target_root(pytestconfig: pytest.Config) -> Path:
    root = Path(pytestconfig.getoption("--aitms-target-root")).resolve()
    if not root.exists():
        pytest.fail(f"Target project root does not exist: {root}")
    return root


@pytest.fixture(scope="session")
def backend_dir(target_root: Path) -> Path:
    path = target_root / "backend"
    if not path.exists():
        pytest.fail(f"Backend directory does not exist: {path}")
    return path


@pytest.fixture(scope="session")
def frontend_dir(target_root: Path) -> Path:
    path = target_root / "frontend"
    if not path.exists():
        pytest.fail(f"Frontend directory does not exist: {path}")
    return path


@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config) -> str:
    return str(pytestconfig.getoption("--aitms-base-url")).rstrip("/")


@pytest.fixture(scope="session")
def frontend_url(pytestconfig: pytest.Config) -> str:
    return str(pytestconfig.getoption("--aitms-frontend-url")).rstrip("/")


@pytest.fixture(scope="session")
def auth_credentials(csv_dedicated_account: dict[str, Any]) -> tuple[str, str]:
    return str(csv_dedicated_account["username"]), str(csv_dedicated_account["password"])


@pytest.fixture(scope="session")
def admin_credentials_from_csv() -> tuple[str, str]:
    case = csv_test_account_case("admin_login_success")
    payload = csv_test_account_json_field(case, "body_json")
    username = str(payload.get("username") or "")
    password = str(payload.get("password") or "")
    if not username or not password:
        pytest.fail("CSV admin login case must include username and password.")
    return username, password


@pytest.fixture(scope="session")
def backend_app_module(backend_dir: Path):
    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault("CONFIG_ENCRYPTION_KEY", "pytest-local-config-key")
    os.environ.setdefault("LOG_LEVEL", "WARNING")

    backend_path = str(backend_dir)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    previous_cwd = Path.cwd()
    try:
        os.chdir(backend_dir)
        return importlib.import_module("src.main")
    except ModuleNotFoundError as exc:
        pytest.fail(
            "Backend dependencies are missing. Install the backend requirements "
            f"or run with a Python environment that can import FastAPI modules. Missing: {exc}"
        )
    finally:
        os.chdir(previous_cwd)


@pytest.fixture(scope="session")
def app(backend_app_module):
    return backend_app_module.app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def live_session() -> Iterator["requests.Session"]:
    import requests

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def live_openapi_schema(live_session, base_url: str) -> dict:
    import requests

    try:
        response = live_session.get(f"{base_url}/api/v1/openapi.json", timeout=10)
    except requests.RequestException as exc:
        pytest.skip(f"Backend is not running at {base_url}: {exc}")
    if response.status_code != 200:
        pytest.fail(f"OpenAPI endpoint returned {response.status_code}: {response.text[:300]}")
    return response.json()


@pytest.fixture(scope="session")
def authenticated_session(base_url: str, auth_credentials: tuple[str, str]):
    import requests

    username, password = auth_credentials
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    response = session.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if response.status_code != 200:
        pytest.fail(f"Login failed for configured user {username!r}: {response.status_code} {response.text[:300]}")

    token = response.json().get("access_token")
    if not token:
        pytest.fail("Login response did not include access_token.")

    session.headers.update({"Authorization": f"Bearer {token}"})
    try:
        yield session
    finally:
        session.close()


def csv_test_account_cases() -> list[dict[str, str]]:
    if not CSV_TEST_ACCOUNT_DATA_PATH.exists():
        pytest.fail(f"CSV test account data does not exist: {CSV_TEST_ACCOUNT_DATA_PATH}", pytrace=False)

    with CSV_TEST_ACCOUNT_DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = CSV_TEST_ACCOUNT_REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            pytest.fail(f"CSV test account data missing columns: {sorted(missing)}")
        return list(reader)


def csv_test_account_case(case_id: str) -> dict[str, str]:
    for case in csv_test_account_cases():
        if case["case_id"] == case_id:
            return case
    pytest.fail(f"CSV test account case does not exist: {case_id}")


def csv_test_account_json_field(case: dict[str, str], column: str) -> Any:
    raw = (case.get(column) or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"{case['case_id']} has invalid JSON in {column}: {exc}")


def csv_test_account_render(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        rendered = value
        for placeholder, replacement in replacements.items():
            rendered = rendered.replace(placeholder, replacement)
        return rendered
    if isinstance(value, list):
        return [csv_test_account_render(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: csv_test_account_render(item, replacements) for key, item in value.items()}
    return value


def csv_test_account_assert_status(response: "requests.Response", expected: str, action: str) -> None:
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


def csv_test_account_extract_id(payload: dict[str, Any]) -> int:
    candidates = [
        payload.get("id"),
        payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("user", {}).get("id") if isinstance(payload.get("data"), dict) else None,
        payload.get("user", {}).get("id") if isinstance(payload.get("user"), dict) else None,
    ]
    for value in candidates:
        if value is not None:
            return int(value)
    pytest.fail(f"CSV test account response does not contain a user id: {payload!r}")


def csv_test_account_extract_roles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        payload.get("roles"),
        payload.get("data", {}).get("roles") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("user", {}).get("roles") if isinstance(payload.get("data"), dict) else None,
        payload.get("user", {}).get("roles") if isinstance(payload.get("user"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def csv_test_account_request(
    session: "requests.Session",
    base_url: str,
    case: dict[str, str],
    replacements: dict[str, str],
) -> "requests.Response":
    path = csv_test_account_render(case["path"], replacements)
    params = csv_test_account_render(csv_test_account_json_field(case, "params_json"), replacements)
    body = csv_test_account_render(csv_test_account_json_field(case, "body_json"), replacements)
    kwargs: dict[str, Any] = {"params": params, "timeout": 10}
    if case["method"].upper() in {"POST", "PUT", "PATCH"}:
        kwargs["json"] = body
    return session.request(case["method"].upper(), f"{base_url}{path}", **kwargs)


def csv_login_admin_from_csv(base_url: str) -> tuple["requests.Session", dict[str, Any]]:
    if requests is None:
        pytest.fail("requests is required for CSV-managed live account tests.")

    case = csv_test_account_case("admin_login_success")
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    response = csv_test_account_request(session, base_url, case, {})
    csv_test_account_assert_status(response, case["expected_status"], "CSV admin login")
    payload = response.json()
    token = payload.get("access_token")
    assert token, f"CSV admin login did not return access_token: {payload!r}"
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, payload


def csv_create_dedicated_account_from_csv(base_url: str) -> dict[str, Any]:
    admin_session, _admin_login = csv_login_admin_from_csv(base_url)
    run_id = uuid.uuid4().hex[:10]
    replacements = {"{{unique}}": run_id, "{{unique_lower}}": run_id.lower()}
    account: dict[str, Any] | None = None

    try:
        create_case = csv_test_account_case("dedicated_user_create")
        create_body = csv_test_account_render(csv_test_account_json_field(create_case, "body_json"), replacements)
        create_response = csv_test_account_request(admin_session, base_url, create_case, replacements)
        csv_test_account_assert_status(create_response, create_case["expected_status"], "CSV dedicated user create")
        created = create_response.json()
        user_id = csv_test_account_extract_id(created)

        account = {
            "user_id": user_id,
            "username": str(create_body["username"]),
            "email": str(create_body["email"]),
            "password": str(create_body["password"]),
            "requested_role_ids": list(create_body.get("role_ids") or []),
            "create_case_id": create_case["case_id"],
            "create_response": created,
        }

        assign_case = csv_test_account_case("dedicated_user_assign_role")
        assign_response = csv_test_account_request(
            admin_session,
            base_url,
            assign_case,
            {**replacements, "{{dedicated_user_id}}": str(user_id)},
        )
        csv_test_account_assert_status(assign_response, assign_case["expected_status"], "CSV dedicated user role assignment")
        detail_response = admin_session.get(f"{base_url}/api/v1/users/{user_id}", timeout=10)
        csv_test_account_assert_status(detail_response, "200", "CSV dedicated user detail after role assignment")
        detail = detail_response.json()
        roles = csv_test_account_extract_roles(detail)
        account["assign_case_id"] = assign_case["case_id"]
        account["assign_status_code"] = assign_response.status_code
        account["detail_response"] = detail
        account["role_ids"] = [int(role["id"]) for role in roles if role.get("id") is not None]
        account["role_codes"] = [str(role["code"]) for role in roles if role.get("code") is not None]
        return account
    except Exception:
        if account is not None:
            csv_delete_dedicated_account_from_csv(base_url, account)
        raise
    finally:
        admin_session.close()


def csv_login_dedicated_from_csv(base_url: str, account: dict[str, Any]) -> tuple["requests.Session", dict[str, Any]]:
    if requests is None:
        pytest.fail("requests is required for CSV-managed live account tests.")

    case = csv_test_account_case("dedicated_user_login_success")
    replacements = {
        "{{dedicated_username}}": str(account["username"]),
        "{{dedicated_password}}": str(account["password"]),
    }
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    response = csv_test_account_request(session, base_url, case, replacements)
    csv_test_account_assert_status(response, case["expected_status"], "CSV dedicated user login")
    payload = response.json()
    token = payload.get("access_token")
    assert token, f"CSV dedicated user login did not return access_token: {payload!r}"
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, payload


def csv_delete_dedicated_account_from_csv(base_url: str, account: dict[str, Any]) -> None:
    user_id = account.get("user_id")
    if user_id is None:
        return

    admin_session, _admin_login = csv_login_admin_from_csv(base_url)
    try:
        response = admin_session.delete(f"{base_url}/api/v1/users/{user_id}", timeout=10)
        assert response.status_code in {200, 202, 204, 400, 404}, (
            f"CSV dedicated user cleanup failed: {response.status_code} {response.text[:500]}"
        )
    finally:
        admin_session.close()


@pytest.fixture(scope="session")
def csv_dedicated_account(base_url: str) -> Iterator[dict[str, Any]]:
    account = csv_create_dedicated_account_from_csv(base_url)
    try:
        yield account
    finally:
        csv_delete_dedicated_account_from_csv(base_url, account)


class LiveCleanupStack:
    """Reverse-order cleanup stack for data created by live tests."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []

    def add(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._callbacks.append(callback)
        return callback

    def discard(self, callback: Callable[[], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def run(self) -> None:
        errors: list[str] = []
        while self._callbacks:
            callback = self._callbacks.pop()
            try:
                callback()
            except Exception as exc:  # pragma: no cover - only runs after live test body.
                errors.append(str(exc))
        if errors:
            pytest.fail("Live test cleanup failed: " + " | ".join(errors))


@pytest.fixture
def live_cleanup_stack() -> Iterator[LiveCleanupStack]:
    stack = LiveCleanupStack()
    try:
        yield stack
    finally:
        stack.run()
