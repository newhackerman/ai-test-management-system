# Run the test suites and write the report

## Input

- Take the framework directory and the case inventory from the case generation step.
- Take the running deployment. Confirm every health endpoint answers 200 before running anything.

## Run in order

- Run the smoke suite first. Stop when smoke is red and fix the client or the deployment before going further.
- Run the full API suite with a JSON report file. It includes the route-coverage guard: a red guard means the app grew a route the tests do not cover — add the route to the tour before calling the suite green.
- Run the E2E suite in a real browser after the API suite passes, page tour first, then the module flows. The tour opens every static route; a page that fails the tour is a defect, not a flaky test, until proven otherwise.
- Record the raw counts for every run: total, passed, failed, error and skipped.

## Tell a flaky test from a defect

- E2E tests are flaky by nature (slow render, a late API response, a
  timing race). A failure is not a defect until it reproduces.
- Rerun only the failures first: `python -m pytest --lf -q`. If a test
  passes on the rerun with no code changed, run it alone once more;
  if it passes again, mark it flaky in the report with the failure
  text, do not file it as a defect, and do not delete it.
- For a suite that is chronically flaky, run with
  `python -m pytest --reruns 1 -q` so a single transient failure does
  not fail the whole run — but the report must still list every test
  that needed a rerun. A rerun is a warning, never a pass.
- A failure that reproduces twice in a row, or that reproduces after
  the app was restarted, is a defect. File it.

## Triage every failure

- Reproduce each failure by hand before calling it a defect. A wrong token attribute, a missing fixture field or a stale selector is a test bug, not a product defect.
- For E2E failures, read the collected page errors before anything else: uncaught page exceptions, console errors and failed API responses are attached to every page visit by the tour helpers. A page that returns 200 but renders an error boundary or a blank body is a product defect, not a pass.
- Fix the test bugs and rerun only the affected module. Keep a count of test bugs fixed per round.
- File the remaining failures as defects with a reproduction, the expected result and the actual result.
- Never change a test expectation to make a failure pass. Fix the test when the test is wrong and fix the app when the app is wrong, and say which one it was.

## Write the report

- Generate the numbers with `tools/report.py` from the JSON report file. It writes `reports/generated.md` — the fresh numbers for this run only.
- Merge those numbers by hand into the curated `reports/TEST_REPORT.md`, which keeps the round history and the defect list. Never let the generator write over the curated file: a wholesale rewrite erases the history. For a fresh project with no curated history yet, the generated file may be used as the first report.
- Add the per-module counts, the round history and the defect list with severity and priority.
- Add a coverage section: routes visited by the tour vs total routes in the router, and the known gaps with their written reasons. A 100 percent pass rate with unvisited routes is reported as partial coverage, never as full.
- Report the final regression only after a run on a clean database. A 100 percent pass rate is claimed only for that final clean run, never for a run that skipped the failing cases.
- Write failures honestly. A failure that was fixed mid-round stays in the round history. A test that needed a rerun to pass is listed as flaky, not as a clean pass.

## Hand off

- Hand the next step the report and the defect list ordered by priority, with the worst defects first.
- Leave the tree with the failing tests still failing when a defect is not yet fixed. Do not delete or skip a failing test to make the suite green.
- Do not fix application code here. Fixing belongs to the fix step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
