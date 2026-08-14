# Pytest Test Framework for AI Test Management System

This pytest project tests `D:\pythonTtest\ai-test-management-system` from outside the application repository.

## Quick Start

```powershell
cd D:\pythonTtest\pytest
python -m pytest D:\pythonTtest\pytest\tests -c D:\pythonTtest\pytest\pytest.ini --aitms-target-root D:\pythonTtest\ai-test-management-system -m "not live and not e2e"
```

Generate HTML and JUnit reports:

```powershell
.\scripts\run_tests.ps1
```

Run tests against a running backend:

```powershell
.\scripts\run_tests.ps1 -WithLive -BaseUrl http://127.0.0.1:8000
```

Run only smoke tests:

```powershell
python -m pytest D:\pythonTtest\pytest\tests -c D:\pythonTtest\pytest\pytest.ini -m smoke --aitms-base-url http://127.0.0.1:8000
```

Run regression tests:

```powershell
python -m pytest D:\pythonTtest\pytest\tests -c D:\pythonTtest\pytest\pytest.ini -m regression --aitms-base-url http://127.0.0.1:8000
```

Run closed-loop business CRUD tests:

```powershell
python -m pytest D:\pythonTtest\pytest\tests\test_live_business_crud_csv_cases.py -c D:\pythonTtest\pytest\pytest.ini -m business_crud --aitms-base-url http://127.0.0.1:8000
```

Run live frontend/backend tests. API login is CSV-managed through `test_cases/test_account_case_data.csv`:

```powershell
.\scripts\run_tests.ps1 -WithLive -BaseUrl http://127.0.0.1:8000 -FrontendUrl http://localhost:3000
```

Run browser E2E tests:

```powershell
python -m pytest D:\pythonTtest\pytest\tests -c D:\pythonTtest\pytest\pytest.ini -m e2e --aitms-frontend-url http://localhost:3000
```

Run with Allure:

```powershell
.\scripts\run_allure_tests.ps1 -BaseUrl http://127.0.0.1:8000 -FrontendUrl http://localhost:3000
```

Double-click full run:

```text
run_full_allure_report.bat
```

The batch file runs the full pytest suite, generates the Allure report, rebuilds trend data, opens the report in the browser, and keeps a local report server running until the window is closed.

`scripts/run_allure_tests.ps1` automatically copies the latest previous report `history` directory into the new `allure-results/history` before generating the next report. This is required for Allure overview trend charts; multiple timestamped report folders alone do not create trend data.

Repair trend data for an already generated report:

```powershell
.\scripts\rebuild_allure_history.ps1 -ReportRoot reports\allure-report -TargetReport reports\allure-report\<timestamp>
```

Run a targeted Allure report for one test file:

```powershell
.\scripts\run_allure_tests.ps1 -TestPath D:\pythonTtest\pytest\tests\test_live_business_edge_coverage.py -BaseUrl http://127.0.0.1:8000 -Marker live
```

Allure is expected at `D:\pythonTtest\allure-2.29.0`. The script writes timestamped results and reports under:

- `reports/allure-results/{timestamp}`
- `reports/allure-report/{timestamp}`

The timestamp format and output directory templates are configured in `pytest.ini`:

- `aitms_allure_timestamp_format`
- `aitms_allure_results_template`
- `aitms_allure_report_template`

## Coverage Scope

- Backend repository structure and required entrypoints
- Python source syntax validation under `backend/src`
- FastAPI application import and in-process health endpoint smoke tests
- OpenAPI generation, critical route group registration, duplicate route detection
- OpenAPI-generated endpoint case catalog under `test_cases/`
- One pytest catalog case per OpenAPI operation
- One pytest live probe case per GET operation
- One pytest anonymous-guard case per protected mutation operation where the probe is non-destructive
- Invalid query/path/body parameter tests expanded from the OpenAPI snapshot
- CSV-managed account workflow in `test_cases/test_account_case_data.csv`: login as `admin` / `Admin123!`, create a dedicated `pytest_auto_dedicated_*` account, assign the highest-privilege `SUPER_ADMIN` role (`id=3`), and verify dedicated-account login. Creating the dedicated user is itself a live test case.
- Login business cases for valid credentials, invalid username/password combinations, missing/empty/null/wrong-type fields, injection payloads, special characters, Unicode/emoji, overlong values, malformed JSON, remember-me, token refresh, logout, and lockout behavior with a disposable account created from CSV-managed data.
- Detailed business cases for roles, users, projects, test plans, test cases, defects, including negative payloads, not-found checks, duplicate checks, permission assignment errors, and cleanup-safe role CRUD
- Business edge cases for prompt templates, dashboards, tasks, milestones, progress, notifications, quality metrics, and requirement traceability, using read-only calls and nonexistent-resource failure paths to avoid persistent test data
- Stable read-only success-path coverage for test executions, defects, and config management detail/permission checks using existing live records
- Stable read-only and query-validation coverage for meetings, risks, reports, requirements, requirement reviews, test-requirement integration, cost control, and multilingual modules
- Deep business workflow coverage for project -> requirement -> test plan -> test case -> execution -> defect/report traceability
- Deep unstable-module coverage for dashboard data, quality metrics, requirement traceability, prompt templates, and AI assistant workspace; these tests assert expected business behavior even when the current backend returns defects
- CSV-managed feature probes in `test_cases/feature_probe_case_data.csv` cover every OpenAPI tag with normal and abnormal representative cases across auth, user/role/permission, project, requirement, testing, defect, risk/task/progress/milestone, meeting, AI, dashboard, config, quality/performance/security, and system operations. These probes assert business-success or controlled 4xx behavior, so unfinished features surface as test failures.
- Closed-loop business CRUD coverage for configuration, configuration groups, project risks, project tasks, meetings, requirements, milestones, and AI model configuration. Test data is created with a `PYTEST_AUTO_*` prefix and each test registers reverse-order cleanup for only the data it created.
- CSV-managed CRUD coverage in `test_cases/business_crud_case_data.csv`, including one login case plus normal and abnormal cases for projects, configuration, configuration groups, risks, tasks, meetings, requirements, milestones, AI model configuration, test plans, test cases, defects, and generated test reports. Authenticated CSV CRUD tests bootstrap through the CSV admin credentials, create a dedicated test account, log in with that dedicated account, and fail rather than skip when the backend cannot complete the workflow.
- Closed-loop testing-management CRUD coverage for test plans, test cases, defects, and generated test reports. Test execution mutation is covered with a controlled no-residue negative case because the OpenAPI surface exposes create/start and complete operations but no delete endpoint for execution records.
- Anonymous access rejection for sensitive API groups
- Frontend package configuration checks for Vite/React/TypeScript
- Optional live HTTP smoke tests for an already running backend
- Live OpenAPI contract tests and authenticated API smoke tests
- Frontend SPA route and static asset availability checks
- Frontend main-menu direct route checks for dashboard, project/task/requirement/risk, AI assistant, meetings, test management, reports, system management, auto recovery, and statistics
- Browser E2E login-page and anonymous-route guard checks
- Smoke/regression classification for live tests, with smoke reserved for core health and availability checks and regression covering the broader API surface
- `business_crud` marker for focused CRUD regression runs. Current split: 36 smoke tests and 2634 regression tests.

## Generated Case Catalog

```powershell
python .\scripts\generate_openapi_case_catalog.py --base-url http://127.0.0.1:8000
```

Generated files:

- `test_cases/api_endpoint_case_catalog.csv`
- `test_cases/business_crud_case_data.csv`
- `test_cases/feature_probe_case_data.csv`
- `test_cases/api_endpoint_case_summary.json`

## Allure Report

Do not open Allure `index.html` directly with `file://`; the report loads JSON assets by HTTP.

```powershell
.\scripts\serve_allure_report.ps1 -Port 8088
```

The server picks the newest timestamped report directory when one exists. Then open `http://127.0.0.1:8088/`.

To inspect raw Allure results and retry/skip breakdowns:

```powershell
python .\scripts\analyze_allure_results.py .\reports\allure-results\<timestamp>
```
- `test_cases/openapi_snapshot.json`

## Notes

- The target backend venv currently does not import `fastapi`; use the global Python environment or install `backend/requirements.txt` into the target venv before running app-level tests there.
- Tests marked `live` require the backend service to be running.
- Live API credentials are managed in `test_cases/test_account_case_data.csv`; command-line credential flags are not required for the CSV-managed live suites.
- Tests marked `e2e` are reserved for future browser workflows once stable login test data is available.
