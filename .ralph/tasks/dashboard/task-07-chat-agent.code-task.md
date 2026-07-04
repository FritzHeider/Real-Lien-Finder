---
status: pending
created: 2026-07-04
---
# Task: Gemini Chat Agent (Docked Panel, Tools, Propose-Then-Confirm)

## Description
Build the persistent docked chat panel backed by Gemini: read-only data
tools that execute immediately, and mutating tools (`propose_config_change`,
`propose_run`) that only ever render a confirmation card — never write to
disk or spawn a process on their own. Implements catalog item #33.

## Background
Seventh task of the dashboard feature, and the highest-trust-boundary one:
this is the only task wiring an LLM to actions that can trigger the pipeline
or (in a future task) modify config. The propose-then-confirm pattern is a
hard requirement, not a nice-to-have — verified explicitly in acceptance
criteria and tests below.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` ("Chat Agent" section in full)
- `run.py`'s `resolve_web_use_dir()` for how `WEB_USE_DIR`/`.env` resolution
  already works — this task reuses the same `GEMINI_API_KEY`, resolved the
  same way, rather than inventing a second config mechanism.

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. `app/api/chat/route.ts`: proxies a Gemini chat completion (function-
   calling enabled), reading `GEMINI_API_KEY` from `WEB_USE_DIR/.env` (same
   resolution logic as `run.py`'s `resolve_web_use_dir`, adapted to
   TypeScript — default `../Web-Use`, override via `WEB_USE_DIR` env var).
2. Read-only tools (execute immediately, call `lib/data.ts` from task 2 —
   no duplicated parsing):
   - `get_ledger_data(county?, dateRange?)`
   - `get_run_history(limit?)`
   - `get_county_config(county)`
3. Mutating tools (**must never execute a side effect directly**):
   - `propose_config_change(county, field, newValue, reason)` — validates
     the field/type (e.g. `max_steps` must be a positive integer) and, if
     valid, returns a structured "proposal" object for the UI to render as a
     confirm card (diff view: field, old value, new value, reason). Invalid
     proposals return a rejection the chat can explain, never a partial
     write.
   - `propose_run(county?)` — returns a structured proposal for the UI to
     render as a "Run {county|all} now?" confirm card. Does **not** call
     `/api/trigger` itself.
   - The confirm card's "Apply"/"Run" button calls the real mutating routes
     directly (a config-write route this task adds for `propose_config_change`
     confirms, and the existing `/api/trigger` from task 5 for `propose_run`
     confirms) — the tool functions themselves have zero side effects.
4. `components/ChatPanel.tsx`: collapsible docked panel in the root layout
   (mount point reserved by task 1), open/closed state persisted in
   `localStorage`, visible on all 4 pages.
5. Chat/Gemini failures (missing/invalid key, rate limit, API error) show an
   inline error state within the panel only — must not throw an error that
   affects any other part of the page.

## Dependencies
- Task 2 (`task-02-data-layer.code-task.md`)
- Task 5 (`task-05-runs-page-trigger.code-task.md`) — `propose_run` confirms
  call the trigger route this task builds.

## Implementation Approach
1. Implement the Gemini client + function-calling wiring in the chat route.
2. Implement the three read-only tools against `lib/data.ts`.
3. Implement the two mutating tools as pure validate-and-return-a-proposal
   functions — no filesystem/subprocess access inside them.
4. Add the config-write route (`POST /api/counties/[slug]`) that only the
   confirm-card button calls, never the tool function itself.
5. Build the panel UI: message list, input, confirm-card rendering for
   proposals.
6. Verify manually: ask the chat about real ledger/run data, ask it to
   propose a `max_steps` change, confirm it, and check the YAML file actually
   changed only after clicking confirm — not when the proposal first
   appeared.

## Acceptance Criteria

1. **Read-only tools return real data**
   - Given real ledger/run-history/county data
   - When asking the chat a question requiring `get_ledger_data`,
     `get_run_history`, or `get_county_config`
   - Then the tool executes immediately and the response reflects the actual
     on-disk data

2. **Mutating tools never write or spawn without explicit confirm**
   - Given a chat request that would call `propose_config_change` or
     `propose_run`
   - When the tool is invoked
   - Then no file is written and no subprocess is spawned as a direct result
     of the tool call — only a proposal object is returned; a unit test
     asserts this (e.g. by spying on the filesystem/spawn calls used
     elsewhere and confirming they're never invoked from these two tool
     functions)

3. **Confirming a proposal executes exactly the same code path as the UI buttons**
   - Given a rendered config-change or run proposal card
   - When clicking "Apply"/"Run"
   - Then the same route (`/api/counties/[slug]` or `/api/trigger`) that the
     Counties/Runs pages' own buttons call is invoked — verified by the write
     actually landing (config file changed / run triggered) only after this
     click

4. **Chat failures are isolated**
   - Given a missing or invalid `GEMINI_API_KEY`
   - When the chat panel attempts a request
   - Then an inline error shows in the panel only, and the rest of the
     dashboard (other pages, other panel state) continues working normally

## Metadata
- **Complexity**: High
- **Labels**: dashboard, chat-agent, gemini, trust-boundary
- **Required Skills**: LLM function-calling, React, Next.js Route Handlers
