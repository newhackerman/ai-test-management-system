# Submit the QA work on a branch and open a PR

## Input

- Take the clean tree, the passing full suite and the updated report from the fix step.
- Take the repository remote and the base branch name, usually main.

## Confirm before submitting

- Submitting pushes code to a shared remote and opens a pull request. Ask the user before doing any of it.
- Present first what will be submitted: the branch name, the files, the commit plan and the draft pull request title and body.
- Wait for the answer. Proceed only on a yes.
- When the user declines, stop and leave the working tree untouched.
- A request to test alone is not approval to submit.

## Prepare the branch

- Confirm the full suite passes on a clean database before creating the branch. A branch built on a red suite wastes the reviewer's time.
- Create a new branch named after the work, such as `qa/automation-framework`.
- Commit in logical chunks: the framework first, then the defect fixes grouped by area, then the recovery scripts, then the report.
- Write each commit message so it says what changed and why in one line.
- Never commit a secret, a password or a token. Read the repository ignore file before the first commit.

## Push and open the pull request

- Push the branch and confirm the remote holds every local commit.
- Check whether a pull request already exists for the branch before creating one.
- Open the pull request with a title that names the framework and the defect count, and a body that states the test results, the defects fixed with their severity, the unrepaired items and how to verify the work.
- Confirm the pull request is open and report its URL to the user.
- Do not skip the confirmation above even when the user approved submitting for another project.

## Hand off

- Report the branch, the commit count, the pull request URL and the final test counts.
- Leave the working tree clean and the branch tracking the remote.
- Stop here. Further review comments belong to a new round of the fix step.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.
- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.
