# Lien Prospecting — Master Prompt

## Objective

Build a daily-automated, config-driven lien-prospecting watch. It finds homeowners with newly-recorded tax or contractor liens across a growing list of counties — dogfooding the Web-Use browsing agent (a separate sibling project, `../Web-Use` by default) for the page-reading step, with deterministic Python owning ledger correctness (dedup/append) rather than leaving that to model judgment.

Adding a county in the future must require only a new YAML config file, never a code change.

## Prerequisite

This project depends on a working Web-Use checkout at `WEB_USE_DIR` (env var, defaults to `../Web-Use`). Before starting Task 3 or later, verify that path exists and contains `src/cli.py` and a working `.env` with `GOOGLE_API_KEY`. If it doesn't, stop and report the problem rather than proceeding — don't attempt to vendor or recreate Web-Use's code inside this project.

## Required Reading

Before doing anything, read the full design spec:

- `.ralph/specs/lien-prospecting/design.md`

Do not deviate from it without flagging the deviation explicitly in your output. If you find the spec ambiguous or wrong about something as you implement, say so and propose the fix rather than silently improvising.

## Execution Order

Work through these task files **in order**, one at a time. Each is fully self-contained (description, requirements, acceptance criteria) — read the task file itself, not just this list, before starting it. Do not start a task whose dependency (noted in its `## Dependencies` section) isn't yet complete.

1. `.ralph/tasks/lien-prospecting/task-01-county-config-schema.code-task.md`
2. `.ralph/tasks/lien-prospecting/task-02-remaining-county-configs.code-task.md`
3. `.ralph/tasks/lien-prospecting/task-03-run-py-extraction.code-task.md`
4. `.ralph/tasks/lien-prospecting/task-04-run-py-ledger.code-task.md`
5. `.ralph/tasks/lien-prospecting/task-05-run-py-error-handling-summary.code-task.md`
6. `.ralph/tasks/lien-prospecting/task-06-summary-output-contract.code-task.md`
7. `.ralph/tasks/lien-prospecting/task-07-skill-md.code-task.md`
8. `.ralph/tasks/lien-prospecting/task-08-scheduling-e2e-validation.code-task.md`

## Per-Task Loop

On each iteration:

1. Find the first task file (in the order above) whose YAML frontmatter has `status: pending` or `status: in_progress` and whose dependencies are `completed`.
2. If none found and all 8 are `completed`: this feature is done — see "Completion" below.
3. Set that task's frontmatter `status: in_progress` and `started: <today's date>` if not already set.
4. Implement exactly what that task file specifies — no more, no less. Do not jump ahead to a later task's work even if it seems convenient.
5. Run whatever tests/validation the task's acceptance criteria imply (unit tests for tasks 1-6, a real ad-hoc run for tasks 7-8).
6. Only when every acceptance criterion in the task file is genuinely met: set `status: completed` and `completed: <today's date>` in that task's frontmatter, then commit.
7. If you get blocked (a site's structure doesn't match what the task assumed, a dependency is missing, etc.), do NOT mark the task completed. Leave it `in_progress`, write what you learned and what's blocking you at the bottom of the task file under a `## Blocker Notes` section (add it if absent), and stop this iteration.

## Global Constraints

- Keep files under 500 lines.
- Validate input at system boundaries (this applies directly to Task 3's JSON parsing and Task 4's CSV loading — never trust the agent's output or an existing ledger file to be well-formed).
- Never commit `.env`, ledger CSVs, or `run.log` — `.gitignore` in this repo already covers these paths; if new runtime-state paths appear during implementation, add them to `.gitignore` immediately rather than waiting for Task 8.
- Use `uv run` for all Python execution, both in this project and when invoking Web-Use's `src/cli.py` (with `cwd` set to `WEB_USE_DIR` — see the Prerequisite section above and the design doc).
- This project does not vendor, copy, or reimplement any of Web-Use's code — it only shells out to `src/cli.py` as an external dependency.

## Completion

When all 8 tasks have `status: completed` in their frontmatter, and Task 8's end-to-end validation genuinely passed (a real run across all 3 counties, a real cron entry created, everything committed): output the line `LOOP_COMPLETE` and stop.

Do not output `LOOP_COMPLETE` early. A task with skipped tests, an untested acceptance criterion, or a "should work" instead of a verified run does not count as complete.
