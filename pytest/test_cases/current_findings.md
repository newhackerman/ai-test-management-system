# Current Interface Test Findings

## Latest Full Allure Run

Run on 2026-08-03:

```powershell
.\scripts\run_allure_tests.ps1 -BaseUrl http://127.0.0.1:8000 -FrontendUrl http://localhost:3000 -Reruns 0 -TimeoutSeconds 30
```

Result: 2466 passed, 197 failed, 1 error, 11 skipped, 3 warnings, 2674 collected.

- Allure results: `reports/allure-results/20260803_192230`
- Allure report: `reports/allure-report/20260803_192230`
- Local report URL: `http://127.0.0.1:8089/`

The teardown error is a cleanup failure for an auto-created config: deleting `PYTEST_AUTO_CONFIG_9cd07ee7d0` returned 403 `无权限删除该配置`.

## Latest CSV-Managed Live Gate Run

Run on 2026-08-03:

```powershell
python -m pytest tests\test_live_test_account_csv_cases.py tests\test_live_auth_login_cases.py tests\test_live_feature_probe_csv_cases.py tests\test_live_business_crud_csv_cases.py -q --tb=short
```

Result: 92 passed, 22 failed, 0 skipped.

Confirmed coverage:

- `test_cases/test_account_case_data.csv` stores the admin bootstrap login (`admin` / `Admin123!`), dedicated account creation data, `SUPER_ADMIN` role assignment data (`role_ids: [3]`), and dedicated account login data.
- `tests/test_live_test_account_csv_cases.py::test_dedicated_user_creation_case_from_csv` covers creating the dedicated test user as a live test case and verifies that the created user detail contains `SUPER_ADMIN`.
- `auth_credentials` and `authenticated_session` no longer skip when command-line credentials are absent; they use the CSV-managed dedicated account.
- `tests/test_live_auth_login_cases.py` no longer has missing-credential or lockout opt-in skips. The lockout test creates its own disposable CSV-managed account.
- `test_cases/feature_probe_case_data.csv` covers every OpenAPI tag with at least one normal and one abnormal representative probe.
- `test_cases/business_crud_case_data.csv` includes one CSV login case, one normal config CRUD closed loop, and one abnormal config-create case.

Current failures from this run:

- Auth boundary: uppercase dedicated username is accepted with status 200. Verify whether username matching is intended to be case-insensitive.
- Auth boundary: emoji, Chinese, and 512-character usernames return 500 instead of controlled 4xx.
- Permissions: `GET /api/v1/permissions` returns 500 because the database is missing `permissions.permission_type`.
- User role management: `GET /api/v1/user-role-management/roles` returns 500.
- Requirement changes: search and invalid-ID paths return 500 due `RequirementChangeService.__init__() got an unexpected keyword argument 'db'`.
- Requirement traceability, progress, milestones, prompt templates, AI model config, Baidu provider, dashboard metric, and quality metrics still return 500 on representative normal or abnormal probes.
- Config permissions: dedicated account gets 403 for config list and config create, even after CSV assignment of the highest-privilege `SUPER_ADMIN` role (`id=3`).
- Settings validation: `PUT /api/v1/settings` accepts `{}` with 200 instead of rejecting invalid payload with 4xx.

Run context:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://localhost:3000`
- OpenAPI paths: 637
- OpenAPI operations: 740
- Latest full live non-E2E result: 2144 passed, 31 failed, 9 skipped, 3 deselected
- Current pytest collection size after read-only/security additions: 2187 tests
- Current pytest collection size after business edge coverage additions: 2373 tests
- Current pytest collection size after smoke/regression split additions: 2382 tests
- Current pytest collection size after operational module read-only additions: 2524 tests
- Current pytest collection size after frontend menu and system read-only additions: 2555 tests
- Current pytest collection size after deep unstable module business additions: 2593 tests
- Current pytest collection size after closed-loop business CRUD additions: 2600 tests
- Current pytest collection size after testing-management CRUD additions: 2605 tests.
- Current pytest collection size after configuration-group CRUD additions: 2606 tests.
- Current pytest collection size after CSV-managed CRUD login/normal/abnormal additions: 2610 tests.
- Current pytest collection size after CSV-managed all-feature probe additions: 2670 tests.
- Current smoke/regression split: 36 smoke tests, 2634 regression tests.
- Coverage marker collection: 64 tests.
- Business CRUD marker collection: 16 tests.
- Latest business CRUD Allure result on 2026-08-03: 8 passed, 5 failed, 0 skipped, 13 total. Results: `reports/allure-results/business_crud_20260803_120655`; report: `reports/allure-report/business_crud_20260803_120655`.
- Latest business CRUD retry summary: 5 tests retried, 15 extra attempts recorded, maximum attempts per failed test was 4.
- Allure retry/timeout policy is configured in `pytest.ini`: failed cases rerun 3 times, rerun delay is 5 seconds, and per-test timeout is 30 seconds.
- Allure timestamp/results/report directory templates are configured in `pytest.ini`. `scripts/run_allure_tests.ps1` reads `aitms_allure_timestamp_format`, `aitms_allure_results_template`, and `aitms_allure_report_template`.
- Historical note: the older root-level `reports/allure-results` directory contained stale skipped results from before the CSV-managed account flow. Use timestamped runs or the latest CSV-managed live gate result above for current skip status.
- Latest authenticated full Allure run after testing-management CRUD additions: report `reports/allure-report/20260730_211850`, results `reports/allure-results/20260730_211850`, final aggregated status is 2427 passed, 163 failed, 3 broken, 12 skipped, 2605 total. This run was completed by resuming a previously interrupted full run; raw result files total 3121 because Allure stores retry attempts and a small number of resumed overlapping attempts.
- Older authenticated skipped breakdown before the CSV lockout change: 7 WebSocket/streaming paths were intentionally not probed with `requests`, 3 Playwright browser starts failed in this Windows environment with `[WinError 5] 拒绝访问。`, and 1 user-delete soft-delete test was skipped to avoid residue.
- Latest backend health check on 2026-07-30: `GET http://127.0.0.1:8000/health` returned 200. The newly added testing-management CRUD tests were live-executed.
- Latest smoke run result: 31 passed, 4 failed, 1 skipped. Failures are frontend `localhost:3000` connection refused plus existing permissions/user-role-management 500 defects.
- Backend health recheck: `GET /health` returned 200 and OpenAPI still exposes 637 paths.
- Latest cleanup residue check after the configuration-group CRUD run: configs/test, config groups, risks, tasks, meetings, requirements, test plans, test cases, defects, and reports all returned 0 visible `PYTEST_AUTO` records.
- Business edge coverage standalone result: 51 passed, 65 failed
- Operational/system module read-only standalone result: 48 passed
- Frontend main-menu route standalone result: 42 passed
- Latest key subset result: 102 passed
- Deep business workflow result: 5 passed, 9 failed
- Deep unstable module business file collection: 24 tests collected. Live execution is pending because the backend at `http://127.0.0.1:8000` refused connections during the latest run.
- Expanded live non-E2E result including abnormal parameters: 2019 passed, 27 failed, 8 skipped, 3 deselected
- Abnormal parameter standalone result: 715 passed, 9 failed
- Current pytest collection size: 2057 tests
- Current pytest collection size after expanded login business cases: 2103 tests
- Current pytest collection size after role/user/project/testing business cases: 2154 tests
- Current pytest collection size after success-path management coverage additions: 2160 tests
- Login business case result: 41 passed, 4 failed, 1 skipped
- Role/User/Project/Test business case result: 49 passed, 2 failed
- Targeted success-path extension run: 87 passed, 13 failed
- Browser E2E result: 3 passed
- Closed-loop CRUD result: role and user API paths were probed; user deletion is soft-delete and is now skipped by default to avoid residue.

## Failing Areas

1. Duplicate FastAPI route registrations

- `GET /api/v1/requirements/statistics`
- `GET /api/v1/test-cases/{case_id}`
- `GET /api/v1/test-reports/allure`
- `GET /api/v1/users/export`
- `POST /api/v1/test-cases/batch-update`
- `POST /api/v1/test-cases/copy`
- `POST /api/v1/test-reports/allure/demo`
- `POST /api/v1/users/batch`
- `POST /api/v1/users/import`

2. Missing OpenAPI tags

- `GET /`
- `GET /api/v1/health`
- `GET /api/v1/performance/alerts`
- `GET /api/v1/performance/paths`
- `GET /api/v1/performance/report`
- `GET /api/v1/performance/stats`
- `GET /health`
- `GET /health/di`

3. Requirement change endpoints return 500 or reset connections

- `GET /api/v1/requirement-changes/impact-analysis/{requirement_id}`
- `GET /api/v1/requirement-changes/pending-approvals`
- `GET /api/v1/requirement-changes/requirement/{requirement_id}`
- `GET /api/v1/requirement-changes/search`
- `GET /api/v1/requirement-changes/statistics`
- `GET /api/v1/requirement-changes/{change_request_id}`
- `POST /api/v1/requirement-changes/impact-analysis`
- `PUT /api/v1/requirement-changes/{change_request_id}`

Observed service-constructor errors include:

- `RequirementChangeService.__init__() got an unexpected keyword argument 'db'`
- `EnhancedImpactAnalysisService.__init__() got an unexpected keyword argument 'db'`

4. User role management endpoints return 500

- `GET /api/v1/user-role-management/permissions`
- `GET /api/v1/user-role-management/permissions/modules`
- `GET /api/v1/user-role-management/roles`

5. Dashboard websocket status endpoint returns 500

- `GET /api/v1/dashboards/ws/connections/status`
- Detail: `no running event loop`

6. Additional connection-reset endpoints

- `GET /api/v1/defects/`
- `GET /api/v1/requirement-reviews/`
- These endpoints are documented as unstable and are excluded from repeated bulk probes to avoid disrupting the running backend.

7. Closed-loop create failures

- `POST /api/v1/projects` returns 500 with `项目创建失败`
- `POST /api/v1/permissions` returns 500 because the service inserts `permission_type`, but the current database table does not have that column
- `GET /api/v1/permissions` returns 500 for the same `permission_type` column mismatch

8. User cleanup behavior is soft-delete

- `DELETE /api/v1/users/{user_id}` marks test users as `status=deleted` / `is_active=false`, but records remain searchable.
- The user CRUD closed-loop test is skipped by default unless `AITMS_ALLOW_SOFT_DELETE_CRUD=1` is set.

9. Login boundary failure

- `POST /api/v1/auth/login` with an overlong username returns 500 instead of a controlled 4xx response.
- `POST /api/v1/auth/login` with the uppercase dedicated username and valid dedicated-account password returns 200. This means username matching is case-insensitive or normalized; verify whether this is intended.
- `POST /api/v1/auth/login` with emoji or Chinese username returns 500 instead of a controlled 4xx response.
- Lockout-after-10-failures is now executed with a disposable CSV-managed account; no lockout opt-in skip remains in `tests/test_live_auth_login_cases.py`.

10. Project and test plan not-found handling

- `GET /api/v1/projects/999999999` returns 500 instead of 404/4xx.
- `GET /api/v1/test-plans/999999999` returns 500 instead of 404/4xx.

11. Detailed business cases added

- Role management: create/get/update/activate/deactivate/delete, invalid payloads, duplicate code, nonexistent role, system-role delete rejection, invalid permission assignment.
- User management: auth/me, profile, list search/pagination/sort, invalid create payloads, nonexistent user operations, self-delete/self-lock rejection.
- Project/Test management: list availability, invalid project create, nonexistent project/test-plan/test-case/defect operations, invalid test-plan/test-case/defect create payloads.
- Auth/security negative cases: invalid bearer token, missing refresh payload, missing login body, CORS preflight, self-delete rejection.
- Read-only validation cases: authenticated core read-only endpoint availability, pagination boundary validation, enum validation, invalid path parameter validation.
- Prompt template, dashboard, task, milestone, progress, notification, quality metric, and requirement traceability edge cases: read-only JSON availability, query validation, nonexistent resource behavior, invalid action payloads, and dashboard selector validation.
- Smoke/regression split: smoke covers health/openapi/core settings/cache-preheating checks; regression covers the broader read-only API surface and controlled failure paths.

12. Prompt template routing and service failures

- `GET /api/v1/prompt-templates/` returns 500 instead of a template list response.
- Static prompt template routes are shadowed by `/{template_id}` and return integer path parsing 422:
  - `GET /api/v1/prompt-templates/categories`
  - `GET /api/v1/prompt-templates/visibility-options`
- `GET /api/v1/prompt-templates/user/my-templates` returns 500.
- Many nonexistent prompt-template read/action paths return 500 instead of 404/4xx, including detail, versions, latest version, render, usage, rollback, test, batch test, and evaluation paths.

13. Dashboard module service/dependency failures

- `GET /api/v1/dashboards/widgets/definitions` returns 500: `WidgetService.get_available_widgets() got an unexpected keyword argument 'category'`.
- `GET /api/v1/dashboards/widgets/categories` returns 500: `WidgetService` has no `get_widget_categories`.
- `GET /api/v1/dashboards/color-schemes/` returns 500 because existing Chinese category values do not match the enum values expected by the ORM.
- Dashboard data endpoints return 500 for both valid and invalid selectors due to `async_generator` not supporting the asynchronous context manager protocol:
  - `/api/v1/dashboards/data/overview`
  - `/api/v1/dashboards/data/statistics/summary`
  - `/api/v1/dashboards/data/metrics/{metric_type}`
  - `/api/v1/dashboards/data/real-time/{data_type}`
  - `/api/v1/dashboards/data/trends/{trend_type}`

14. Additional business edge failures

- Quality metric read/action endpoints return 500 instead of successful read responses or controlled 4xx validation errors:
  - `GET /api/v1/quality-metrics/dashboard`
  - `GET /api/v1/quality-metrics/health-check`
  - `POST /api/v1/quality-metrics/calculate`
  - `POST /api/v1/quality-metrics/monitor`
  - `POST /api/v1/quality-metrics/trends/analyze`
  - `POST /api/v1/quality-metrics/improvements/suggest`
  - `POST /api/v1/quality-metrics/benchmarks/analyze`
- Requirement traceability list/detail/coverage/orphan/consistency endpoints return 500 in read-only or nonexistent-resource paths.
- Task detail for nonexistent ID returns 500 instead of 404/4xx; task dependency validation for nonexistent task also returns 500.
- Milestone detail/dependency/statistics/timeline and complete/reopen/impact-analysis paths return 500 for nonexistent IDs instead of 404/4xx.
- Progress trend and alert acknowledge/resolve paths return 500 for nonexistent IDs instead of 404/4xx.

15. Newly verified healthy endpoints

- `GET /api/v1/test-executions/64`
- `GET /api/v1/test-executions/64/logs`
- `GET /api/v1/defects/14`
- `GET /api/v1/defects/14/comments`
- `GET /api/v1/configs/configs`
- `GET /api/v1/configs/configs/codex.page.check.1780371232?environment=prod&decrypt=false`
- `GET /api/v1/configs/environments/prod/statistics`
- `GET /api/v1/configs/import-export/formats`
- `GET /api/v1/configs/validation-rules/rule-templates`
- `GET /api/v1/configs/advanced-permissions/templates`
- `GET /api/v1/configs/advanced-permissions/user/1/effective?config_key=codex.page.check.1780371232&environment=prod`
- `GET /api/v1/configs/permissions/check?config_key=codex.page.check.1780371232&environment=prod&action=READ`
- `POST /api/v1/configs/validation-rules/build-rule` accepts an empty JSON body and returns 200, so it is now treated as a successful probe.

16. Newly verified operational module read-only coverage

- Meetings: list and project meeting types.
- Risks: list, alerts, analysis, health, monitor status, and trend.
- Reports: Allure list, analytics, formats, imported list, and unified report list.
- Requirements: global list, project list, and statistics.
- Requirement reviews: review list.
- Test requirement integration: health endpoint.
- Cost control: alerts, model metrics, performance metrics, and usage patterns.
- Multilingual: supported language list.
- Dashboard/system: dashboard access, dashboard summary, settings read, and auto-recovery thresholds.
- Controlled 4xx coverage was added for missing risk/report/requirement/test-requirement resources and invalid pagination/enum query parameters.
- Controlled 422 coverage was added for auto-recovery threshold/manual-recovery requests with missing payloads.

17. Newly verified frontend route coverage

- Direct SPA route checks now cover the visible main menu: dashboard, project, task, requirement, risk, AI assistant, meeting, testing overview, test plans, test cases, executions, defects, reports, performance, security, user, role, settings, config, config groups, audit logs, auto recovery, and statistics.

18. Newly verified deep business workflow coverage

- Project 1 -> requirement 17 -> test plan 12 -> test case 178 -> execution 64 -> report chain is consistent.
- Defect 14 traces back to execution 61 and test case 192.
- Requirement 17 detail/history/dependencies and task dependency chain endpoints are available.
- Risk 8 detail, analysis, alerts, and trend endpoints are available.
- Meeting detail loads for meeting 15, but participants/status/summary/minutes and project meeting schedule/statistics endpoints still fail with 500.
- Execution progress for execution 64 still fails with 500.

19. Newly added deep coverage for unstable business modules

- Dashboard business data: overview, statistics summary, project/quality metrics, real-time system status, project progress trend, and test pass rate trend.
- Quality metrics: dashboard, health check, calculate, trend analysis, and improvement suggestions with business request bodies.
- Requirement traceability: link search, requirement traceability, coverage, and matrix generation.
- Prompt templates: list, categories, visibility options, statistics overview, my templates, and search.
- AI assistant workspace: status, health, service info, conversation list, and conversation statistics.
- These tests intentionally expect business-success responses. They are not skipped or xfailed, so current backend 500/422/routing defects will surface directly in reports.

20. Newly added closed-loop business CRUD coverage

- Configuration CRUD: create a test-environment config, read by key, update value/description/tags, list by search, hard-delete, then verify the key returns 404.
- CSV-managed configuration CRUD: `test_cases/business_crud_case_data.csv` drives one login case, one normal create/read/update/search/delete case, and one abnormal create case that omits `config_key` and expects a controlled 4xx response. The CRUD test logs in first using the CSV login case data and fails fast when credentials are missing instead of skipping authenticated coverage.
- Configuration group CRUD: create a `PYTEST_AUTO_*` config group, list and verify visibility, update name/description/icon/color/sort order, soft-delete through the delete endpoint, then verify the enabled group list no longer contains it. Latest live result: passed.
- Risk CRUD: create a project risk, read by ID, update name/level/status/probability, list by search, delete, then verify the ID returns 404.
- Task CRUD: create a project task, read by ID, full update, patch update, list by search, delete, then verify the ID should return 404. Current backend returns 500 on the final not-found read.
- Meeting CRUD: create a scheduled project meeting, read by ID, update title/settings, list by keyword, delete, then verify the ID returns 404.
- Requirement CRUD: create a project requirement, read by ID, update title/priority/business value/effort, list by keyword, delete, then verify the ID should return 404. Current backend returns 500 on the final not-found read.
- Milestone CRUD: create a project milestone, then read/update/search/delete. Current backend returns 500 during create, so downstream milestone CRUD assertions cannot run yet.
- AI model config CRUD: create a custom model config, then read/update/search/delete. Current backend returns 500 during create with `User object has no attribute get`, so downstream CRUD assertions cannot run yet.
- All tests use `PYTEST_AUTO_*` data and `live_cleanup_stack` reverse-order cleanup callbacks so partial creations are cleaned up even when later assertions fail.
- Meeting creation accepts naive ISO datetime strings but returns 500 when the same business payload uses a UTC `Z` suffix.
- Milestone list with `search=PYTEST_AUTO` currently returns 500, so list residue verification cannot use that endpoint until the list defect is fixed.
- AI model config list with `provider=custom` currently returns 500 with the same `User.get` defect, so list residue verification cannot use that endpoint until the permission decorator/service contract is fixed.

21. Newly added testing-management CRUD coverage

- Test plan CRUD: create a `PYTEST_AUTO_*` plan under project 1, read by ID, update plan name/description/strategy/scope/status, search by project and keyword, delete, then verify the deleted plan returns 404.
- Test case CRUD: create an isolated test plan and a `PYTEST_AUTO_*` case, read by ID, update title/description/priority/status/steps/result/tags, search by plan and keyword, delete the case, verify 404, then delete the parent plan.
- Defect CRUD: create an isolated plan and case, create a `PYTEST_AUTO_*` defect linked to that case, read by ID, update title/description/severity/priority/environment, search by case and keyword, delete the defect, verify 404, then delete case and plan.
- Test report closed loop: generate a uniquely named `PYTEST_AUTO_*` report, read by returned report ID, search in report list, delete, then verify 404. Cleanup is registered immediately after a report ID is returned.
- Test execution mutation: covered with a no-residue negative case against a nonexistent test case because OpenAPI exposes manual start/complete but does not expose a delete endpoint for execution records. This keeps the test data policy closed-loop while still validating controlled failure behavior.
- Latest live result for this file: 4 passed, 1 failed. Test case CRUD, defect CRUD, report closed loop, and execution no-residue negative case passed. Test plan CRUD fails only on the final deleted-detail assertion because `GET /api/v1/test-plans/{plan_id}` returns 500 instead of 404 after deletion.
- Defect cleanup handling was hardened: if an auto-created defect cannot be deleted because the backend only allows deleting `NEW` or `REJECTED` defects, cleanup first transitions the `PYTEST_AUTO_*` defect to `REJECTED`, then deletes it.

## Coverage Status

- All 740 operations are in the generated case catalog.
- All 740 operations are expanded into individual pytest catalog cases.
- All operations are checked for minimum OpenAPI metadata.
- `test_cases/feature_probe_case_data.csv` covers every OpenAPI tag with at least one CSV-managed feature probe. Each feature in that CSV has at least one normal probe and one abnormal probe.
- CSV-managed feature probes add 58 live representative cases across auth, user/role/permission, project/team, requirement/review/change/traceability, test management, defects, risks/tasks/progress/milestones, meetings, AI, dashboards, configuration, quality/performance/security, and system operations. Normal probes expect 2xx JSON responses; abnormal probes expect controlled 4xx responses, so 5xx and unfinished functions are reported as bugs.
- All GET operations are expanded into individual live probe cases unless explicitly skipped for websocket/streaming paths.
- Protected mutation operations are expanded into individual anonymous 4xx guard cases without authenticated writes.
- Invalid query parameters, invalid integer path parameters, and malformed JSON bodies are expanded into individual negative test cases from the OpenAPI snapshot.
- CSV-managed CRUD data includes a login case plus at least one normal and one abnormal case, with the data contract covered by `tests/test_live_business_crud_csv_cases.py::test_business_crud_csv_data_includes_normal_and_abnormal_cases`.
- Authenticated closed-loop mutation coverage has started with configuration, risk, task, and meeting modules. More mutation modules can be added using the shared cleanup stack as their API-specific factories become stable.
