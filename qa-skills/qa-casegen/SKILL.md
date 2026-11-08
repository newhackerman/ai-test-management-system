# Analyze an API with AI and generate test cases

## Input

- Take the deployment note and the project profile from the deploy step
  (`qa-automation/PROJECT.md`): the repository path, the running base
  URLs, the health endpoints, the test account, the auth scheme, the
  envelope shape and the deployment shape.
- Take the OpenAPI document when the backend exposes one. When it does not, enumerate the route files and the data models instead.
- Never use, import or copy the repository's own test framework or test code.

## Analyze the API first

- Build an endpoint inventory from the live OpenAPI document: one row per operation with its path, method, auth requirement, request shape and response shape.
- Cross-check the inventory against the route files so undocumented endpoints are not missed.
- When there is no OpenAPI document and no readable route table, use
  these fallbacks in order: (1) GraphQL — run an introspection query
  against the endpoint and build the inventory from the schema;
  (2) frontend API calls — grep the frontend's API client/service
  files for fetch/axios calls and build the inventory from the URLs
  and payloads they use; (3) live probing — exercise the documented
  entry points and record every endpoint the app actually calls.
  Record which fallback was used in the project profile, because the
  inventory from a fallback is partial by construction.
- Read the data models for every entity and note the required fields, the enums and the foreign keys.
- Read the auth module and note how login works, what roles exist and which endpoints check roles.
- Build a frontend route inventory too: parse the router file for every path (static and parameterised) and the sidebar menu. The API inventory alone never proves a page was opened — a route with no test is a gap, not a pass. For an API-only project there is no frontend inventory; say so in the analysis record and skip the tour.
- Write the inventory down as the analysis record. Generate no cases before this record exists.

## Scope a large API before generating

- When the inventory is large (roughly 200 operations or more), do not
  generate cases for every endpoint in one pass. Rank the endpoints by
  risk first: auth and session handling, money and payment flows,
  endpoints that write or delete data, endpoints with role checks, and
  anything the analysis flagged as untested by the repository's own
  suite. Generate the high-risk slice first, run it, then extend.
- State the scope in the case inventory: how many endpoints are covered
  in this round and which ones are deliberately deferred, with the
  reason. A deferred endpoint is an explicit decision, never an
  accident — the same rule as the route-coverage buckets.

## Set up the framework

- Copy `~/workspace/custom-skills/qa-template/` into the repository as `qa-automation/`.
- Adapt it in the five steps its README lists, driven by the project
  profile: set the environment, match the auth and envelope shapes
  through the env switches (`QA_AUTH_SCHEME`, `QA_ENVELOPE`,
  `QA_TOKEN_FIELD`, `QA_APP_ROOT`, `QA_HAS_OPENAPI`) — edit `client.py`
  or `assertions.py` only when the project uses a scheme the switches
  do not cover, and record the exception in `PROJECT.md`. Then add one
  payload builder and one fixture per entity, then write the cases.
- Confirm the adaptation with the template smoke suite before writing any domain case. A red smoke suite means the client or the envelope is still wrong, not that the API is broken.

## Generate cases with AI

- Generate cases per endpoint and per category, in this order: smoke, auth, CRUD, validation, boundary, security, then E2E flows.
- For every endpoint write the happy path first, then the negative cases: missing required fields, wrong types, empty strings, oversized values and boundary numbers.
- For every authenticated endpoint write the unauthenticated case and the wrong-role case.
- For every endpoint that takes an id, write the nonexistent id case and the other user's id case.
- Put data-driven invalid payloads in a JSON file and drive one parametrized test from it instead of copying the same test many times.
- Give every payload a unique name so tests never collide with each other or with prior runs.
- Register best-effort cleanup for every created record so a leftover row never breaks other tests.

## Generate E2E flows with AI

- First, generate the page tour: one parametrized test that logs in and opens every static route from the route inventory, proving each page renders (non-blank, no error boundary, no console errors, no failed API responses). A page no test visits is a page nobody watches.
- Add the route-coverage guard: a test that parses the router file and fails the suite when a route sits in no coverage bucket (tour / module-covered / excluded-with-a-written-reason). New routes must land in a bucket — never nowhere.
- Then read the frontend routes and pick the core user flows: login, create and list each main entity, and one full chain from the first entity to the last.
- Drive the real browser for every E2E case. A 200 from the server never proves the page renders.
- Write one helper per UI creation flow in `e2e/helpers.py`, following the login helper pattern in the template.
- End every creation flow with a visible proof that the record persisted, such as searching for its unique name in the list.
- Spot-check primary actions, not just rendering: a visible button that does nothing when clicked is a defect the render checks cannot see. For each key list page, click its main action and prove something happens (a modal opens, navigation happens, a toast appears).

## Hand off

- Hand the next step the case inventory: how many cases per module and per category, and which areas the analysis flagged as risky.
- Keep the framework free of repository test code. The cases are all original.
- Do not run the full suite here. Running and reporting belong to the execute step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
