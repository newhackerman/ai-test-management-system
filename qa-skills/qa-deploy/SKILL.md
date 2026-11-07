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

## Start the services

- Install the system dependencies the stack needs, preferring the package manager already present on the machine.
- Create the databases and the service accounts, then load the seed data when the repository provides it.
- Start the backend and the frontend and wait for each health endpoint to answer 200.
- When a service fails to start, read its own log first, fix the missing piece and retry. Do not edit application code to make it start unless the failure is a missing dependency or a bad default.
- Prove the deployment with a real request: log in with the default test account and fetch one list endpoint.

## Add self-healing recovery

- Write an idempotent recovery script under the repository's `ops/` directory that rebuilds the whole environment from scratch: reinstall missing packages, recreate the database and the service accounts, rebuild tables and seed data, then restart every service and verify each health endpoint.
- Read every secret from the application's own env file at runtime only. Never commit a password and never print one.
- Add service units that restart the backend and the frontend automatically.
- Add a watchdog that runs the recovery script every 10 minutes and reports only when it repairs something or when it fails.
- Test the recovery by stopping every service and running the script once. Report the result only after all four checks pass: database alive, cache answering, backend health 200 and frontend 200.

## Hand off

- Hand the next step a short note with the stack, the ports, the base commit, the test account location and the health endpoints.
- Keep the working tree clean of test changes at this point. The framework comes next.
- Do not create a branch yet. Branching belongs to the submit step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
