# Deploy the target project for testing

## Entry point

- Take one input from the user and nothing else: a repository URL or a local code path.
- Clone the repository into the workspace when given a URL, or use the given path when given code.
- Record the base commit hash before changing anything.
- Never use, import or copy the repository's own test framework or test code. Read it only to know what coverage already exists.

## Identify the stack

- Read the README, the dependency manifests and the compose or Docker files.
- List the backend language and framework, the frontend framework, the databases and caches, the default ports and the default test account.
- Open the API surface: fetch the OpenAPI document when the backend exposes one, otherwise enumerate the route files.
- Write down the health endpoints for the backend and the frontend before starting anything.

## Pick the deployment shape

Not every project is a backend plus a frontend on one VM. Decide which
shape fits and deploy only what exists:

- **Full-stack** (backend + frontend + database): the default path below.
- **API-only** (no frontend): skip the frontend entirely — no E2E suite,
  no `QA_FRONTEND_URL`. The API suite is the whole framework.
- **Frontend-only** (no backend of its own): the API suite has nothing
  to test; the page tour and the UI flows are the framework. Record the
  backend it talks to, if any, as out of scope.
- **Compose-based** (the repo ships a working `docker compose` file):
  deploy with compose, not with systemd units. `docker compose up -d`
  is the start command; `docker compose down -v && docker compose up -d`
  is the clean-database rebuild. Keep the compose file as the recovery
  mechanism instead of writing `ops/recover.sh`.
- **No database** (stateless service, SQLite file, or an external
  managed database): there is no clean-database rebuild to write. The
  "clean run" for the final regression is a fresh container or a
  reseeded fixture set — say which one in the project profile.

Record the choice in `qa-automation/PROJECT.md` (see "Hand off" below)
so later steps never re-decide it.

## Start the services

- Install the system dependencies the stack needs, preferring the package manager already present on the machine.
- Create the databases and the service accounts, then load the seed data when the repository provides it.
- Start the backend and the frontend and wait for each health endpoint to answer 200.
- When a service fails to start, read its own log first, fix the missing piece and retry. Do not edit application code to make it start unless the failure is a missing dependency or a bad default.
- Prove the deployment with a real request: log in with the default test account and fetch one list endpoint.

## Add self-healing recovery

- Write an idempotent recovery script under the repository's `ops/` directory that rebuilds the whole environment from scratch: reinstall missing packages, recreate the database and the service accounts, rebuild tables and seed data, then restart every service and verify each health endpoint. For a compose-based deployment, skip this script: the recovery is `docker compose down -v && docker compose up -d` plus a health check, written down in the project profile instead.
- Read every secret from the application's own env file at runtime only. Never commit a password and never print one.
- Add service units that restart the backend and the frontend automatically. For a compose-based deployment, use `restart: unless-stopped` in the compose file instead.
- Add a watchdog that runs the recovery script every 10 minutes and reports only when it repairs something or when it fails. For a compose-based deployment, the watchdog runs the compose rebuild command instead.
- Test the recovery by stopping every service and running the script once. Report the result only after all four checks pass: database alive, cache answering, backend health 200 and frontend 200. Skip the checks that do not apply to the deployment shape (no frontend, no cache, no database).

## Hand off

- Write the project profile into `qa-automation/PROJECT.md` (the
  template ships a blank one): stack, deployment shape, ports, base
  commit, test account location, health endpoints, auth scheme and
  envelope shape, app container selector, and how to rebuild a clean
  database. This file — not a chat message — is the handoff. Later
  steps read it instead of re-deriving the same facts.
- Keep the working tree clean of test changes at this point. The framework comes next.
- Do not create a branch yet. Branching belongs to the submit step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
