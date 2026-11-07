# QA Automation Framework

Reusable black-box API test framework for the AI Test Management System.

**Scope**: this framework is written from scratch. It does NOT use, import,
or copy anything from the repository's own `pytest/` directory
(conftest, tests, scripts, case data). All clients, fixtures, factories
and cases here are original.

## Layout

```
qa-automation/
├── README.md            # this file
├── pytest.ini           # pytest configuration (markers, paths)
├── requirements.txt     # pytest + httpx (already in backend/venv)
├── config.py            # settings (env-overridable)
├── client.py            # ApiClient: auth, HTTP verbs, envelope helpers
├── factories.py         # payload builders (unique names via uuid suffix)
├── assertions.py        # shared assertion helpers
├── conftest.py          # fixtures: client, login, project factory, cleanup
├── data/
│   └── negative_cases.json   # data-driven invalid-payload cases
├── tests/
│   ├── test_smoke.py
│   ├── test_auth.py
│   ├── test_projects.py
│   ├── test_requirements.py
│   ├── test_test_cases.py
│   ├── test_test_plans.py
│   ├── test_executions.py
│   ├── test_defects.py
│   ├── test_risks.py
│   └── test_reports.py
├── tools/
│   └── report.py        # Markdown report generator (from pytest json report)
└── reports/             # generated: latest.json + TEST_REPORT.md (gitignored)
```

## Run

```bash
# from the repo root (uses backend/venv which already has pytest + httpx)
cd qa-automation
../backend/venv/bin/python -m pytest -q

# smoke only
../backend/venv/bin/python -m pytest -q -m smoke

# full run with JSON report + Markdown report
../backend/venv/bin/python -m pytest -q \
    --json-report --json-report-file=reports/latest.json
../backend/venv/bin/python tools/report.py
```

## Configuration (env vars)

| Var | Default | Meaning |
|-----|---------|---------|
| `QA_BASE_URL` | `http://127.0.0.1:8000` | backend base URL |
| `QA_ADMIN_USER` | `admin` | admin username |
| `QA_ADMIN_PASSWORD` | `TEST@test1` | admin password |
| `QA_TIMEOUT` | `15` | per-request timeout (s) |

## Extending

To cover a new module, add a test file under `tests/` and reuse:

- `api` fixture — authenticated `ApiClient`
- `project` fixture — a fresh project (auto-deleted after the module)
- `factories.*` — payload builders, e.g. `factories.project_payload()`
- `assertions.*` — `assert_status`, `assert_envelope_ok`, ...

New cases only need a payload + expected status; no new plumbing.

## Page tour and route coverage

The E2E suite opens every page, not just the flows with creation
tests. `e2e/page_tour_routes.py` is the inventory of every static
route; `e2e/test_e2e_page_tour.py` visits each one and proves it
renders (non-blank, no error boundary, no console errors, no failed
API responses). `e2e/helpers.assert_page_renders` collects page
errors, console errors and failed responses for every visit — a 200
never proves the page renders.

`tests/test_route_coverage.py` is the guard: it parses
`frontend/src/routes/index.tsx` and fails the suite when a route sits
in no coverage bucket (tour / module-covered / excluded-with-reason /
param-covered / known-gap). **When you add a route to the app, put it
in a bucket in `e2e/page_tour_routes.py` or the suite goes red.**
Coverage gaps must be explicit decisions, never accidents.
