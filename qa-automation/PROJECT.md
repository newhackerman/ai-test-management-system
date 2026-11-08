# Project profile — ai-test-management-system

This file is the single source of truth for how THIS project is tested.
Written during the deploy step; the casegen, execute and fix steps read
it instead of re-deriving the same facts. When the project changes
(a new auth scheme, a new envelope shape, a moved login page), update
this file first and the framework follows.

## Identity

- Project: ai-test-management-system — https://github.com/newhackerman/ai-test-management-system
- Base commit (before any QA change): main `000a222` (PR #9 merged 2026-11-08)
- Framework copy: `qa-automation/` (copied from the qa-template, synced with the 2026-11-08 optimisation)

## Stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Backend language / framework | Python 3.12, FastAPI + SQLAlchemy + MySQL + Redis + JWT | Code under `backend/src/` |
| Frontend framework | React 18 + TypeScript + Vite (dev server) | Frontend changes hot-reload; backend needs `systemctl restart ai-test-backend` (~15 s to come up) |
| Database | MySQL 8.0.46, database `ai_test_db` | 125 tables on the shared Base; seed 45 permissions / 9 roles |
| Cache / queue | Redis 7.0.15 | Distro unit needed a drop-in (`PrivateUsers=false`) |
| Deployment | systemd units on a VM (`ops/systemd/`) | Backend :8000, frontend :3000 |
| Backend port / URL | :8000 http://127.0.0.1:8000 | |
| Frontend port / URL | :3000 http://localhost:3000 | |

## API surface

- OpenAPI document: `/api/v1/openapi.json` (651 paths, regenerated 2026-11-07)
- Docs page: `/api/v1/docs`
- Route inventory source: live OpenAPI document, cross-checked against route files
- Response envelope (`QA_ENVELOPE`): `success` — `{"success": true, "<resource>": {...}}`; list endpoints additionally serve a plain list envelope (`{"projects": [...], "total": N, ...}`), read directly by the tests
- Auth scheme (`QA_AUTH_SCHEME`): `bearer`
- Login endpoint (`QA_LOGIN_PATH`): `/api/v1/auth/login`
- Token field (`QA_TOKEN_FIELD`): `access_token` (top level); refresh token `refresh_token`
- Login lockout: 3 failures lock 15 min, 5 lock 24 h — locked branch returns **423**; wrong password / unknown user still **401**
- Test account: admin (default credentials in `config.py`; the password lives in `backend/.env`, never in this file)

## E2E

- App container (`QA_APP_ROOT`): `#root` (React)
- Login page (`QA_LOGIN_PAGE`): `/login`
- Login selectors: `#username` / `#password`, button text `登录`
- Dashboard marker (text visible only after login): `项目总数`
- Logout button: `退出`
- Router file: `frontend/src/routes/index.tsx` (61 routes; 33 in the tour, 13 parameterised routes are known gaps — see `e2e/page_tour_routes.py`)

## Environment rebuild (clean database)

- How to get a clean database: `bash ops/recover.sh` — reinstalls missing packages, recreates the database, rebuilds tables + seed via `ops/rebuild_db.py`, restores the newest hourly backup when its table count matches (best-effort), restarts Redis/backend/frontend, verifies health
- Seed data: 45 permissions / 9 roles; rebuild verifies the counts
- Recovery script: `ops/recover.sh` (log `/tmp/ai-test-recover.log`, timestamps UTC)
- Hourly backup: `ops/backup_db.sh` → `~/backups/ai-test-db/`, keeps latest 7; cron `ai-test-db-backup`
- Watchdog: cron `ai-test-env-watchdog`, every 10 min, runs `ops/recover.sh`
- Note: the VM is replaced often without warning and the replacement wipes the database — the watchdog + hourly backup are the safety net, not an edge case

## Health endpoints

- Backend: `GET /api/v1/health` → 200 (`{"status": "ok"}`); also `GET /health` → 200 (`{"status": "healthy"}`)
- Frontend: `GET /` → 200
- Cache: `redis-cli ping` → PONG

## Known quirks

- Backend takes ~15 s to come up after a restart; wait for the health endpoint, do not assume.
- The antd static-message console warning (`[antd: message] Static function can not consume context`) is allowlisted as benign in `e2e/helpers.py` — dev-mode warning, not a failure.
- Blank threshold for the page tour is 100 body characters (the app shell alone is ~150; a white screen is ~0–20).
- Headless recording limitation: ffmpeg needs PulseAudio + X11 (absent); recordings end FAILED and ffmpeg leaves a defunct zombie process per recording start.
- ChangeImpactAnalysis page is NOT mounted (only exported); its trigger list is also unmounted — recorded in the report, no UI entry.
- `get_prompt_service` does not exist (startup preheat ImportError is swallowed each boot).
- The repository's own `pytest/` suite is read-only for coverage awareness — never imported, reused or copied.
