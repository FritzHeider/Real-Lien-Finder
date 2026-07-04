# Lien Prospecting Dashboard — Master Prompt

## Objective

Build a local, tool-packed web dashboard for the existing lien-prospecting
pipeline: view ledger data, monitor/trigger runs, inspect county configs, and
talk to a Gemini-powered chat agent that can explain data and propose (never
silently apply) config changes or run triggers. This dashboard only reads and
drives `run.py` through interfaces that already exist (CLI args, YAML files,
`SUMMARY_JSON` stdout contract) — it never changes pipeline behavior.

## Prerequisite

Same as the underlying pipeline: a working `../Web-Use` checkout at
`WEB_USE_DIR` (defaults to `../Web-Use`), with `src/cli.py` and a `.env`
containing `GEMINI_API_KEY`. The dashboard's chat agent (task 7) reuses this
same key rather than requiring a second one. Verify this before starting task
7; if missing, stop and report rather than inventing a separate config
mechanism.

## Required Reading

Before doing anything, read the full design spec:

- `.ralph/specs/dashboard/design.md`

Do not deviate from it without flagging the deviation explicitly in your
output, in the same style already used in
`.ralph/specs/lien-prospecting/design.md`'s own flagged deviations. If you
find the spec ambiguous or wrong about something as you implement, say so and
propose the fix rather than silently improvising.

## Execution Order

Work through these task files **in order**, one at a time. Each is
fully self-contained — read the task file itself, not just this list,
before starting it. Do not start a task whose dependency (noted in its
`## Dependencies` section) isn't yet complete.

1. `.ralph/tasks/dashboard/task-01-nextjs-scaffold.code-task.md`
2. `.ralph/tasks/dashboard/task-02-data-layer.code-task.md`
3. `.ralph/tasks/dashboard/task-03-overview-page.code-task.md`
4. `.ralph/tasks/dashboard/task-04-liens-page.code-task.md`
5. `.ralph/tasks/dashboard/task-05-runs-page-trigger.code-task.md`
6. `.ralph/tasks/dashboard/task-06-counties-page.code-task.md`
7. `.ralph/tasks/dashboard/task-07-chat-agent.code-task.md`
8. `.ralph/tasks/dashboard/task-08-testing-and-e2e.code-task.md`

## Per-Task Loop

On each iteration:

1. Find the first task file (in the order above) whose YAML frontmatter has
   `status: pending` or `status: in_progress` and whose dependencies are
   `completed`.
2. If none found and all 8 are `completed`: this feature is done — see
   "Completion" below.
3. Set that task's frontmatter `status: in_progress` and
   `started: <today's date>` if not already set.
4. Implement exactly what that task file specifies — no more, no less. Do
   not jump ahead to a later task's work even if it seems convenient. The
   40-item catalog in the design spec is a backlog reference, not a to-do
   list for this loop — only the 10 items marked `[v1]` (mapped to these 8
   tasks) are in scope.
5. Run whatever tests/validation the task's acceptance criteria imply (unit
   tests for tasks 1-7, a real ad-hoc walkthrough for task 8).
6. Only when every acceptance criterion in the task file is genuinely met:
   set `status: completed` and `completed: <today's date>` in that task's
   frontmatter, then commit.
7. If you get blocked (a dependency is missing, an acceptance criterion
   can't be met as written, etc.), do NOT mark the task completed. Leave it
   `in_progress`, write what you learned and what's blocking you at the
   bottom of the task file under a `## Blocker Notes` section (add it if
   absent), and stop this iteration.

## Global Constraints

- Keep files under 500 lines.
- Validate input at system boundaries — this applies directly to task 2's
  YAML/CSV/JSONL parsing, matching the same principle `run.py` already
  follows.
- Never commit `dashboard/node_modules/`, `dashboard/.next/`, or
  `dashboard/.data/` (runs.jsonl runtime state) — add to `.gitignore`
  immediately if any new runtime-state path appears during implementation,
  rather than waiting for task 8.
- This dashboard never modifies `run.py` or its `SUMMARY_JSON` output
  contract. It spawns `run.py` as a subprocess exactly as a human would from
  the CLI — it does not vendor, copy, or reimplement any of its logic.
- The chat agent's mutating tools (`propose_config_change`, `propose_run`)
  must never execute a write or spawn a process directly — this is a hard
  requirement verified by tests in task 7, not a style preference.

## Completion

When all 8 tasks have `status: completed` in their frontmatter, and task 8's
end-to-end validation genuinely passed (a real live walkthrough, not a
simulated one, with the existing Python test suite still green): output the
line `LOOP_COMPLETE` and stop.

Do not output `LOOP_COMPLETE` early. A task with skipped tests, an untested
acceptance criterion, or a "should work" instead of a verified run does not
count as complete.
