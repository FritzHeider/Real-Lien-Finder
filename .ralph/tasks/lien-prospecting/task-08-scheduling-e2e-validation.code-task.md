---
status: pending
created: 2026-07-01
started: null
completed: null
---
# Task: Daily Scheduling + End-to-End Validation

## Description
Wire up the daily cron job that invokes the lien-prospecting skill, and validate the full pipeline end-to-end against real county sites before considering the feature done.

## Background
This is the final task in the lien-prospecting feature. Everything up to this point (configs, extraction, ledger, error handling, summary contract, skill docs) has been built and unit-tested individually; this task proves the whole thing actually works together against live sites and puts it on a schedule.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (full document — this task is the integration point for everything in it)

**Additional References:**
- `.claude/skills/lien-prospecting/SKILL.md` (Task 7) — the skill this task schedules

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. Use the `/schedule` mechanism (CronCreate) to create one daily cron entry whose prompt invokes the lien-prospecting skill (e.g. "Invoke the lien-prospecting skill and run it for all configured counties, then notify me of the results.").
2. Confirm the schedule was created by listing it back, and report the exact cadence/time to the user before treating this as done.
3. Run at least one full end-to-end pass across all 3 configured counties (not just Maricopa) manually, confirming:
   - Configs load correctly for all three.
   - Each county's sources either produce parsed results or a clean, logged failure (no unhandled exceptions).
   - Ledger CSVs are created/updated correctly under `scripts/lien_prospecting/ledger/`.
   - The `SUMMARY_JSON:` line is emitted correctly.
   - A push notification is actually sent (or correctly skipped if the run was quiet) by following through on the skill's documented follow-up step.
4. Add `scripts/lien_prospecting/ledger/` and `scripts/lien_prospecting/run.log` to `.gitignore` — these are runtime state, not source, and must not be committed.
5. Commit all new source files: `scripts/lien_prospecting/` (excluding ledger/log per gitignore), `.claude/skills/lien-prospecting/`, `.ralph/specs/lien-prospecting/`, `.ralph/tasks/lien-prospecting/`.

## Dependencies
- Task 7 (`task-07-skill-md.code-task.md`)

## Implementation Approach
1. Add the gitignore entries first.
2. Run `uv run python scripts/lien_prospecting/run.py` (all counties, no `--county` filter) manually and inspect the output/ledgers/log.
3. Use `/schedule` to create the daily cron job; verify it's listed.
4. Commit.

## Acceptance Criteria

1. **Cron job exists**
   - Given the `/schedule` (CronCreate) invocation completes
   - When the schedule is listed
   - Then exactly one daily entry exists that invokes the lien-prospecting skill

2. **End-to-end run succeeds across all 3 counties**
   - Given a manual run of `run.py` with no county filter
   - When it completes
   - Then all 3 counties appear in the summary, each either with a new-row count (possibly 0) or a `failed_sources` entry — never an unhandled exception — and the process exits 0

3. **Runtime state is gitignored, source is committed**
   - Given `git status` after a completed run
   - When checking tracked vs. ignored paths
   - Then `scripts/lien_prospecting/ledger/` and `run.log` do not appear as trackable/stageable changes, while `run.py`, the county YAMLs, and the SKILL.md are committed

## Metadata
- **Complexity**: Medium
- **Labels**: scheduling, deployment, validation, lien-prospecting
- **Required Skills**: cron/schedule tooling, git, manual QA
