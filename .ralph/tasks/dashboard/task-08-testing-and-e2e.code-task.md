---
status: pending
created: 2026-07-04
---
# Task: Testing Pass + Manual End-to-End Walkthrough + Polish

## Description
Close out v1: fill any test gaps left by tasks 1-7, then do a real, live
end-to-end walkthrough of the whole dashboard before calling it done — no UI
feature is "complete" on the strength of unit tests alone.

## Background
Final task of the dashboard v1 feature. Mirrors how the underlying
lien-prospecting pipeline itself was closed out
(`.ralph/tasks/lien-prospecting/task-08-scheduling-e2e-validation.code-task.md`):
individually-tested pieces must be proven to work together against the real
pipeline before the feature counts as done.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` (full document — this task is
  the integration/verification point for everything in it)
- All prior task files in `.ralph/tasks/dashboard/` for their individual
  acceptance criteria — this task confirms they still hold together as one
  app, not in isolation.

## Technical Requirements
1. Confirm test coverage exists for:
   - `lib/data.ts` parsers (task 2)
   - Chat's mutating-tool-never-writes-directly guarantee (task 7)
   - Trigger route's SSE streaming and concurrency lock (task 5)
   Fill any gaps found.
2. Run `npm run build` (or equivalent) to confirm a production build
   succeeds with no type errors.
3. Manual end-to-end walkthrough, performed for real (not simulated) against
   this actual repo:
   - Start the dashboard (`npm run dev`), confirm all 4 pages load.
   - Trigger a real run for one county (e.g. `douglas_co`) from `/runs`,
     watch the live SSE log, confirm it completes and appears in run history
     with accurate per-source detail.
   - View `/liens` and confirm ledger data (including any new rows from the
     run just triggered) renders and filters/sorts correctly.
   - View `/counties` and confirm all 3 counties render correctly, including
     Douglas's `max_steps: 80` override.
   - Use the chat panel to ask a real data question (e.g. "how many liens
     did Douglas find this week"), confirm the answer matches
     `/liens`/`/runs` data.
   - Ask the chat to propose a config change (e.g. adjust a
     `min_lien_amount`), confirm the proposal card appears, click confirm,
     and verify the YAML file actually changed only at that point.
   - Attempt to trigger a second run while one is in progress; confirm it's
     correctly rejected in the UI.
4. Confirm the existing Python test suite (`uv run pytest tests/ -q`, 45
   tests) still passes unmodified — this task must not have touched
   `run.py` or its tests.
5. Add `dashboard/` to the root README as a documented way to run the
   project, alongside the existing CLI/skill instructions.

## Dependencies
- Task 7 (`task-07-chat-agent.code-task.md`)

## Implementation Approach
1. Run the full frontend test suite and the production build; fix any
   failures.
2. Perform the manual walkthrough above, in order, against the real repo
   state — not a mocked/seeded environment.
3. Run the existing Python suite to confirm no regression.
4. Update documentation.
5. Commit.

## Acceptance Criteria

1. **All frontend tests pass and the app builds for production**
   - Given the full test suite and `npm run build`
   - When run
   - Then all tests pass and the build succeeds with no type errors

2. **Live end-to-end walkthrough passes, genuinely performed**
   - Given the real dashboard running against this real repo
   - When performing every step in the Technical Requirements' walkthrough
     list
   - Then each step behaves as specified — a "should work" without having
     actually run it does not satisfy this criterion

3. **Existing Python suite unaffected**
   - Given `uv run pytest tests/ -q`
   - When run after this task's changes
   - Then all 45 (or however many then exist) tests still pass, confirming
     `run.py`'s behavior is untouched

4. **Documentation updated**
   - Given the root `README.md`
   - When reviewed
   - Then it documents how to run the dashboard alongside the existing CLI
     usage

## Metadata
- **Complexity**: Medium
- **Labels**: testing, e2e, dashboard, polish
- **Required Skills**: Vitest, manual QA, Next.js build tooling
