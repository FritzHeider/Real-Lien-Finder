---
status: pending
created: 2026-07-04
---
# Task: Runs Page + Trigger API + Live SSE Log + Concurrency Lock

## Description
Build the `/runs` page (run history + expandable per-source detail) and the
trigger mechanism: `POST /api/trigger` spawns `run.py` exactly as a human
would from the CLI, streams its stdout live via Server-Sent Events, appends
the result to `runs.jsonl`, and enforces a concurrency lock so two runs can
never overlap. Implements catalog items #9, #10, #11, #13.

## Background
Fifth task of the dashboard feature, and the most operationally sensitive
one — this is the only task that spawns a real subprocess (the same one the
daily cron and manual CLI usage already spawn). Must not change `run.py`'s
behavior or output contract in any way; it only wraps it.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` ("Architecture" → triggering a
  run, "Pages & Layout" → `/runs`, "Error Handling" table)
- `scripts/lien_prospecting/run.py` — the exact invocation
  (`uv run python scripts/lien_prospecting/run.py [--county <slug>]`) and the
  `SUMMARY_JSON: {...}` stdout contract this task must parse.

**Note:** Read the design document and `run.py` before beginning
implementation. Do not modify `run.py` — this task only spawns it as a
subprocess, per this project's existing constraint that the pipeline and any
UI on top of it stay decoupled.

## Technical Requirements
1. `POST /api/trigger` (optionally accepting `{county?: string}`):
   - Rejects immediately with a 409-equivalent response if a run is already
     in progress (in-memory lock — single Next.js process, no need for a
     file lock).
   - Spawns `uv run python scripts/lien_prospecting/run.py` (with
     `--county <slug>` if provided), `cwd` at the repo root.
   - Streams stdout line-by-line to the client as Server-Sent Events as the
     process runs.
   - On exit: parses the final `SUMMARY_JSON: {...}` line from the captured
     stdout, calls `appendRunRecord({timestamp, summary})` (task 2), and
     releases the lock. If the process errors/times out before producing a
     `SUMMARY_JSON` line, do **not** append a run record (no phantom runs) —
     surface the raw error to the client instead.
2. `/runs` page:
   - Lists run history from `getRunHistory()` (task 2), newest first:
     timestamp, counties run, new-lien counts, failure summaries.
   - Each row expands to show per-county/per-source detail (mirroring the
     `SUMMARY_JSON` shape: `new` count and `failed_sources` per county).
   - "Run now" controls: one button for all counties, and a per-county
     option (dropdown or per-row buttons, matching `run.py --county`).
   - While a run is in flight: buttons are disabled, a live log panel shows
     the streamed SSE output, and a clear "run in progress" state is visible
     anywhere a new trigger would otherwise be attempted.
3. Reuse `lib/data.ts` (task 2) for all reads/writes — this task adds the
   trigger/streaming logic, not new file-parsing logic.

## Dependencies
- Task 2 (`task-02-data-layer.code-task.md`)
- Task 3 (`task-03-overview-page.code-task.md`) — not a hard technical
  dependency, but keeping page-building sequential avoids layout rework.

## Implementation Approach
1. Implement the in-memory lock (a module-level flag or a small `Set` of
   in-flight run IDs) in the trigger route.
2. Implement subprocess spawn + stdout streaming via SSE
   (`ReadableStream`/`TransformStream` in a Next.js Route Handler).
3. Implement `SUMMARY_JSON` line parsing (reuse the exact marker string
   `run.py` prints: `"SUMMARY_JSON: "` prefix) and wire it to
   `appendRunRecord`.
4. Build the `/runs` page consuming `getRunHistory()` plus a client-side SSE
   subscription for the live log during an active trigger.
5. Manually verify: trigger a real run (e.g. `--county douglas_co`, since
   it's faster than all 3), watch the live log stream, confirm the run
   appears in history afterward, and confirm a second trigger attempt while
   the first is running is correctly rejected.

## Acceptance Criteria

1. **Trigger spawns the real pipeline and streams output**
   - Given the dashboard is running and `../Web-Use` is available
   - When POSTing to `/api/trigger` with `{county: "douglas_co"}`
   - Then `run.py --county douglas_co` is spawned, its stdout streams to the
     client via SSE as it runs, and the process's real exit behavior is
     reflected (success or failure) — not simulated

2. **Concurrent trigger is rejected**
   - Given a run is currently in progress
   - When a second `POST /api/trigger` arrives (from a button or, once task 7
     exists, from chat's `propose_run` confirm)
   - Then it is rejected with a clear "already in progress" response, and no
     second subprocess is spawned

3. **Successful run is recorded, failed run is not**
   - Given a triggered run that completes and prints a `SUMMARY_JSON:` line
   - When it exits
   - Then `runs.jsonl` gains exactly one new record matching that summary
   - Given a triggered run that times out or crashes before printing
     `SUMMARY_JSON`
   - When it exits
   - Then no record is appended, and the client sees a clear error state

4. **Run history and detail render correctly**
   - Given existing entries in `runs.jsonl`
   - When loading `/runs`
   - Then each run appears newest-first with correct summary counts, and
     expanding a row shows accurate per-county/per-source detail matching
     that run's recorded `summary`

## Metadata
- **Complexity**: High
- **Labels**: dashboard, subprocess, sse, runs-page
- **Required Skills**: Next.js Route Handlers, Node child_process, Server-Sent Events
