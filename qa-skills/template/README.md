# QA Automation Template

Black-box test framework skeleton. Copy this directory into the target
repository as `qa-automation/` and adapt the five points below. Nothing
here depends on any one project.

## Layout

```text
qa-automation/
  PROJECT.md           project profile: stack, auth, envelope, rebuild
  config.py            settings, all env-overridable
  client.py            ApiClient: auth, HTTP verbs
  assertions.py        envelope and error assertions
  conftest.py          api/anon fixtures, cleanup helper
  factories.py         payload builders (unique names)
  pytest.ini           markers and paths
  requirements.txt     pytest, httpx, pytest-json-report, playwright
  tests/test_smoke.py  health, docs, openapi, login smoke tests
  tools/report.py      Markdown report generator (writes generated.md)
  e2e/conftest.py      Playwright fixtures
  e2e/helpers.py       login/logout/nav helpers + page-error collection
  e2e/page_tour_routes.py  page-tour inventory (every route in a bucket)
  e2e/test_e2e_smoke.py  login page smoke tests
  e2e/test_e2e_page_tour.py  parametrized tour: every static route renders
  tests/test_route_coverage.py  guard: no route without a coverage bucket
```

## Adapt in 5 steps

1. Fill in `PROJECT.md` first: stack, auth scheme, envelope shape,
   app container, login selectors, health endpoints and how to rebuild
   a clean database. Every later step reads it instead of guessing.
2. Set the environment from `PROJECT.md`: `QA_BASE_URL`,
   `QA_FRONTEND_URL`, `QA_ADMIN_USER`, `QA_ADMIN_PASSWORD`,
   `QA_LOGIN_PATH`, `QA_HEALTH_PATH`, plus the three shape switches
   `QA_AUTH_SCHEME` (bearer / cookie / apikey), `QA_ENVELOPE`
   (success / code / bare) and `QA_APP_ROOT` (#root / #app /
   app-root). Token field names go in `QA_TOKEN_FIELD`. Only when the
   project uses a scheme the switches do not cover (basic auth, OAuth)
   do you edit `client.py` — that is the one code adaptation point.
   Set `QA_HAS_OPENAPI=0` when the backend serves no OpenAPI document.
3. Add one `factories.<entity>_payload` builder and one
   `conftest.make_<entity>` fixture per domain entity, copying the
   commented example in each file.
4. Write one `tests/test_<module>.py` per API module, one
   `e2e/test_e2e_<flow>.py` per user flow. Cover smoke, auth, CRUD,
   validation, boundary, security and E2E in that order. Before the
   flows, fill in `e2e/page_tour_routes.py` from the router file and
   sidebar: every static route goes in the tour, every other route in
   a coverage bucket with a reason. Run the tour first — a page no
   test visits is a page nobody watches.
5. Run `python -m pytest -q` and then `python tools/report.py` for the
   Markdown report.

## Run

```bash
cd qa-automation
python -m pytest -q -m smoke
python -m pytest --json-report --json-report-file=reports/latest.json
python tools/report.py   # writes reports/generated.md (this run's numbers)
```

`tools/report.py` writes `reports/generated.md` only. The curated
`reports/TEST_REPORT.md` keeps the round history and the defect list:
merge the numbers from `generated.md` into it by hand. Never point
the tool at the curated file — a wholesale rewrite would erase the
history. For a fresh project with no curated history yet, pass the
output path explicitly: `python tools/report.py reports/latest.json
reports/TEST_REPORT.md`.

## Rules the template follows

- Never import or copy the target repository's own test code.
- Every payload carries a unique name so tests never collide.
- Cleanup is best-effort and a leftover row never breaks other tests.
- A passing run is only claimed after a clean-database final regression.
- Every E2E page visit collects page errors, console errors and failed
  API responses. A 200 never proves the page renders.
- Every route sits in a coverage bucket (tour / module-covered /
  excluded-with-reason). A new route with no bucket fails the suite.
- Adaptation is configuration, not code: auth scheme, envelope shape,
  token fields and the app container are env settings. Edit `client.py`
  or `assertions.py` only when the project uses a scheme the switches
  do not cover, and record the exception in `PROJECT.md`.
- The generated report (`reports/generated.md`) and the curated report
  (`reports/TEST_REPORT.md`) are different files. The generated one is
  disposable numbers; the curated one is the history. Never let the
  generator overwrite the curated file.
