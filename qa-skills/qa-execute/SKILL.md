# Run the test suites and write the report

## Input

- Take the framework directory and the case inventory from the case generation step.
- Take the running deployment. Confirm every health endpoint answers 200 before running anything.

## Run in order

- Run the smoke suite first. Stop when smoke is red and fix the client or the deployment before going further.
- Run the full API suite with a JSON report file.
- Run the E2E suite in a real browser after the API suite passes.
- Record the raw counts for every run: total, passed, failed, error and skipped.

## Triage every failure

- Reproduce each failure by hand before calling it a defect. A wrong token attribute, a missing fixture field or a stale selector is a test bug, not a product defect.
- Fix the test bugs and rerun only the affected module. Keep a count of test bugs fixed per round.
- File the remaining failures as defects with a reproduction, the expected result and the actual result.
- Never change a test expectation to make a failure pass. Fix the test when the test is wrong and fix the app when the app is wrong, and say which one it was.

## Write the report

- Generate the Markdown report with `tools/report.py` from the JSON report file.
- Add the per-module counts, the round history and the defect list with severity and priority.
- Report the final regression only after a run on a clean database. A 100 percent pass rate is claimed only for that final clean run, never for a run that skipped the failing cases.
- Write failures honestly. A failure that was fixed mid-round stays in the round history.

## Hand off

- Hand the next step the report and the defect list ordered by priority, with the worst defects first.
- Leave the tree with the failing tests still failing when a defect is not yet fixed. Do not delete or skip a failing test to make the suite green.
- Do not fix application code here. Fixing belongs to the fix step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
