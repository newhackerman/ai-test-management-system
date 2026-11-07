# Fix defects by priority and re-verify

## Input

- Take the defect list ordered by priority and the test report from the execute step.
- Take the repository at the same commit the tests ran against.

## Fix in priority order

- Fix the worst defects first. A defect that breaks login, shows a blank page or lets one user touch another user's data comes before anything else.
- Fix one defect at a time and keep each fix small enough to describe in one sentence.
- Change application code only where the defect lives. Do not refactor nearby code in the same change.
- When a fix needs a migration or a seed change, write it so a fresh database builds cleanly from scratch.

## Verify each fix

- Rerun the affected module right after each fix and confirm the failing case now passes.
- Rerun the full suite on a clean database after all fixes in the round are done.
- Update the report after every round with the new counts and the status of each defect.
- Leave a defect open with its reason when it cannot be fixed in this round. Never delete the case that proves it.

## Dig deeper when the count looks thin

- Treat a small defect count as a reason to test harder, not as a success to report.
- Add a deeper round when the first round found almost nothing: harder inputs, security probing and real-browser flows.
- Verify in a real browser anything a status code could hide, such as a blank page behind a 200 response.

## Hand off

- Hand the next step a clean tree, a passing full suite on a clean database and an updated report with zero unrepaired items or an explicit list of the ones left open.
- Keep every fix on the working branch. Do not commit here. Committing belongs to the submit step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
