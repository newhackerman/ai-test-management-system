# QA Automation Template

Black-box test framework skeleton. Copy this directory into the target
repository as `qa-automation/` and adapt the five points below. Nothing
here depends on any one project.

## Layout

```text
qa-automation/
  config.py            settings, all env-overridable
  client.py            ApiClient: auth, HTTP verbs
  assertions.py        envelope and error assertions
  conftest.py          api/anon fixtures, cleanup helper
  factories.py         payload builders (unique names)
  pytest.ini           markers and paths
  requirements.txt     pytest, httpx, pytest-json-report, playwright
  tests/test_smoke.py  health, docs, openapi, login smoke tests
  tools/report.py      Markdown report generator
  e2e/conftest.py      Playwright fixtures
  e2e/helpers.py       login/logout/nav helpers
  e2e/test_e2e_smoke.py  login page smoke tests
```

## Adapt in 5 steps

1. Set the environment: `QA_BASE_URL`, `QA_FRONTEND_URL`,
   `QA_ADMIN_USER`, `QA_ADMIN_PASSWORD`, `QA_LOGIN_PATH`, `QA_HEALTH_PATH`.
2. Match the auth and envelope: in `client.py` fix the token field names
   and in `assertions.py` fix the success/error envelope shape. This is
   the single most common adaptation.
3. Add one `factories.<entity>_payload` builder and one
   `conftest.make_<entity>` fixture per domain entity, copying the
   commented example in each file.
4. Write one `tests/test_<module>.py` per API module, one
   `e2e/test_e2e_<flow>.py` per user flow. Cover smoke, auth, CRUD,
   validation, boundary, security and E2E in that order.
5. Run `python -m pytest -q` and then `python tools/report.py` for the
   Markdown report.

## Run

```bash
cd qa-automation
python -m pytest -q -m smoke
python -m pytest --json-report --json-report-file=reports/latest.json
python tools/report.py
```

## Rules the template follows

- Never import or copy the target repository's own test code.
- Every payload carries a unique name so tests never collide.
- Cleanup is best-effort and a leftover row never breaks other tests.
- A passing run is only claimed after a clean-database final regression.
