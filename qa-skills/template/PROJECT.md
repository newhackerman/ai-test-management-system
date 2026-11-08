# Project profile — fill in during the deploy step

This file is the single source of truth for how THIS project is tested.
The deploy step writes it; the casegen, execute and fix steps read it
instead of re-deriving the same facts. When the project changes
(a new auth scheme, a new envelope shape, a moved login page), update
this file first and the framework follows.

## Identity

- Project: _name / repo URL_
- Base commit (before any QA change): _hash_
- Framework copy: `qa-automation/` (copied from the qa-template)

## Stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Backend language / framework | _e.g. Python FastAPI_ | |
| Frontend framework | _e.g. React 18 + Vite / Vue 3 / none (API-only)_ | |
| Database | _e.g. MySQL 8 / Postgres / SQLite / none_ | |
| Cache / queue | _e.g. Redis / none_ | |
| Deployment | _systemd units on a VM / docker compose / other_ | |
| Backend port / URL | _e.g. :8000 http://127.0.0.1:8000_ | |
| Frontend port / URL | _e.g. :3000 http://localhost:3000 / n/a_ | |

## API surface

- OpenAPI document: _path, e.g. /api/v1/openapi.json, or "none"_
- Docs page: _path, e.g. /api/v1/docs, or "none"_
- Route inventory source: _OpenAPI / route files / GraphQL introspection / frontend API calls_
- Response envelope (`QA_ENVELOPE`): _success / code / bare_
- Auth scheme (`QA_AUTH_SCHEME`): _bearer / cookie / apikey_
- Login endpoint (`QA_LOGIN_PATH`): _e.g. /api/v1/auth/login_
- Token field (`QA_TOKEN_FIELD`): _e.g. access_token (top level or inside "data")_
- Test account: _username / where the password lives (never the password itself)_

## E2E

- App container (`QA_APP_ROOT`): _#root (React) / #app (Vue) / app-root (Angular)_
- Login page (`QA_LOGIN_PAGE`): _e.g. /login_
- Login selectors: _username / password / button text_
- Dashboard marker (text visible only after login): _e.g. a metric label_
- Router file: _path to the route definitions, for the page tour_

## Environment rebuild (clean database)

- How to get a clean database: _e.g. `bash ops/recover.sh` / `docker compose down -v && docker compose up -d` / seed script_
- Seed data: _what the rebuild loads, and the counts it must verify_
- Recovery script: _path, e.g. ops/recover.sh_
- Watchdog: _cron / compose restart policy / none_

## Health endpoints

- Backend: _e.g. GET /api/v1/health → 200_
- Frontend: _e.g. GET / → 200_
- Cache: _e.g. redis-cli ping → PONG / n/a_

## Known quirks

- _Anything the next step must not rediscover: a slow first boot, a
  flaky endpoint, a route that needs a fixture, a page that legitimately
  renders almost empty, a console error that is known-benign and why._
