# Lien Prospecting Dashboard — Design Spec

## Objective

A local, tool-packed web dashboard for the lien-prospecting pipeline: view ledger
data, monitor/trigger runs, inspect county configs, and talk to a Gemini-powered
chat agent that can explain data and propose (never silently apply) config
changes or run triggers. Read-only against `run.py`'s existing output contract —
this dashboard never changes pipeline behavior, it only observes and drives it
through the same interfaces a human already uses (CLI args, YAML files).

## Scope Decision

- **Local-only.** No auth, no hosting, no database migration. The pipeline's
  dependencies (`../Web-Use` sibling checkout, gitignored ledger CSVs, session-
  scoped cron) are all local — a deployed dashboard would need a parallel
  infrastructure project. Out of scope for this spec.
- **Viewer + run controls.** Can trigger runs and re-runs; cannot edit county
  YAML from the UI directly (that's chat-mediated, propose-then-confirm, or
  hand-editing files) in v1. Full in-UI config editing is backlog (catalog #18).

## Architecture

- **Next.js 14 (App Router), TypeScript, Tailwind + shadcn/ui.** Single process,
  single port (`npm run dev`), no separate backend server.
- **Location**: lives at `dashboard/` in the repo root — a sibling to
  `scripts/`, with its own `package.json`/`node_modules`/lockfile. Kept
  separate from the Python package rather than nested inside
  `scripts/lien_prospecting/`, since it's a distinct app with its own
  toolchain, not a pipeline module.
- **Data sources** (all filesystem, no DB):
  - `scripts/lien_prospecting/counties/*.yaml` — county configs (read from the
    repo root via a relative path resolved the same way `run.py`'s
    `PROJECT_ROOT` is derived)
  - `scripts/lien_prospecting/ledger/*.csv` — per-county ledgers
  - `scripts/lien_prospecting/run.log` — failure log
  - `dashboard/.data/runs.jsonl` — **new**, one JSON line per triggered run
    (`{timestamp, summary}` from `run.py`'s `SUMMARY_JSON` contract). Needed
    because `SUMMARY_JSON` today only exists transiently on stdout; the
    dashboard needs run history across restarts. Lives under the dashboard
    app's own directory (not `scripts/lien_prospecting/`) since it's
    dashboard-specific runtime state, not pipeline state — gitignored.
- **API routes** (`app/api/*`) are the only code that touches the filesystem or
  spawns a subprocess. React components never read files directly — everything
  goes through `lib/data.ts` helpers shared by the routes and the chat tools.
- **Triggering a run**: `POST /api/trigger` spawns
  `uv run python scripts/lien_prospecting/run.py [--county <slug>]` exactly as
  a human would from the CLI, streams stdout line-by-line to the client via
  **Server-Sent Events**, and appends `{timestamp, summary}` to `runs.jsonl` on
  exit. An in-memory lock (single process) rejects a second trigger while one
  is in flight — `run.py` has no concurrency guard of its own, and two
  simultaneous runs risk corrupting a ledger CSV mid-append.
- **No changes to `run.py` or its output contract.** The existing 45-test
  Python suite, the daily cron, and ad-hoc CLI usage are all unaffected.

## Design System

Generated via `ui-ux-pro-max --design-system "internal ops dashboard admin
tool dense data saas"`:

- **Style**: Data-Dense Dashboard (multiple charts/widgets, data tables, KPI
  cards, minimal padding, grid layout — matches a power-user monitoring tool,
  not a marketing site).
- **Colors**: Primary `#1E40AF`, Secondary `#3B82F6`, Accent `#D97706`,
  Background `#F8FAFC`, Foreground `#1E3A8A`, Destructive `#DC2626`. Blue data +
  amber highlights, WCAG AA.
- **Typography**: Fira Code (data/numbers) / Fira Sans (UI text) — dashboard,
  technical, precise mood.
- **Charts**: Recharts. Line chart for trends (per `chart` domain guidance: <4
  points → stat card instead; >6 series → visual noise). Bar chart, not
  pie/donut, for failure-reason breakdown (more than a few reason codes:
  `invalid_json`, `max_steps_exhausted`, `agent_aborted`, `subprocess_error`).
- **Avoid**: ornate decoration, charts/tables without filtering, pie charts for
  >5 categories, color-only meaning (every status also has text/icon).

## Pages & Layout

Persistent left sidebar nav (4 items) + persistent collapsible right-side chat
panel (see below), present on every page.

- **`/` (Overview)** — KPI row (liens found today/this week, active counties,
  last run status), new-liens trend line chart per county, failure-reason
  breakdown bar chart.
- **`/liens`** — Filterable/sortable ledger table aggregating all
  `ledger/*.csv` (county, source kind, date range, min amount). Tabular/
  monospaced numbers per the data-dense style.
- **`/runs`** — Run history from `runs.jsonl` (timestamp, counties run, new-
  lien counts, failures), expandable per-source detail. "Run now" (all
  counties or one) opens a live SSE log panel. Blocked with a clear "run
  already in progress" state while the concurrency lock is held.
- **`/counties`** — Read-only structured viewer of each county YAML (name,
  sources, prompts, `max_steps`, `dedup_key`) — cards, not a raw YAML dump.
  In-UI editing is backlog (catalog #18); v1 edits happen via chat proposals
  or hand-editing files.

## Chat Agent

- **`app/api/chat/route.ts`** — proxies Gemini, reusing the same
  `GEMINI_API_KEY` already configured in `WEB_USE_DIR/.env` (resolved the same
  way `run.py`'s `resolve_web_use_dir()` resolves `WEB_USE_DIR`, so there's one
  key to manage, not two).
- **Read-only tools** (execute immediately — safe): `get_ledger_data(county?,
  dateRange?)`, `get_run_history(limit?)`, `get_county_config(county)`. These
  call the exact same `lib/data.ts` helpers the page routes use — no
  duplicated parsing logic anywhere in the codebase.
- **Mutating tools** (never auto-execute): `propose_config_change(county,
  field, newValue, reason)` and `propose_run(county?)`. Both validate their
  input (e.g. reject a non-numeric `max_steps`) and render as a confirmation
  card in the chat UI — a YAML diff for config changes, a "Run Douglas now?"
  card for runs. Clicking "Apply"/"Run" calls the *same* mutating routes the
  Counties/Runs pages' own buttons use (`POST /api/counties/[slug]`,
  `POST /api/trigger`) — one code path for every write or trigger, regardless
  of whether it originated from a button or from chat.
- **Placement**: `components/ChatPanel.tsx`, a collapsible docked panel in the
  root layout, open/closed state in `localStorage`, present on all 4 pages —
  not a separate nav item, so you can ask "why did Maricopa fail today?" while
  looking at `/runs`.
- Chat/Gemini failures (missing key, rate limit, API error) are isolated to
  the panel — an inline error state there never blocks the rest of the
  dashboard.

## Error Handling

| Failure | Handling |
|---|---|
| Two triggers at once | In-memory lock rejects the second; UI shows "run already in progress" (Runs page buttons and chat's `propose_run` both respect it). |
| Malformed ledger CSV row / `runs.jsonl` line / county YAML | Skipped with a small warning banner in the affected view, not a crashed page — mirrors `run.py`'s own "validate at boundaries" principle. |
| Subprocess/SSE error or timeout | Live log panel shows a clear error state with raw stderr; nothing is appended to `runs.jsonl` for that attempt (no phantom run entries). |
| Chat proposes an invalid config change | Rejected before rendering a confirm card (type/field validation). |
| Confirmed chat change fails to write | Inline failure shown in chat, not silently dropped. |
| Gemini API failure | Isolated inline error in the chat panel only. |

## Testing

- `lib/data.ts` parsers: unit tests (Vitest) for the same edge cases the
  Python suite covers on the source side (missing fields, malformed rows).
- Chat tool-calling: test that `propose_config_change`/`propose_run` never
  write to disk or spawn a process directly — only the explicit confirm
  action (a separately-tested path) does.
- Trigger route: SSE streaming and the concurrency lock, with a mocked child
  process.
- Manual walkthrough before calling v1 done: start the dashboard, trigger a
  real county run, watch the live log, view the ledger table, ask the chat a
  data question, propose a config change and confirm it.
- The existing 45-test Python suite (`tests/`) is untouched — this dashboard
  only reads `run.py`'s output contract, never modifies its behavior.

## Known External Blocker

Several sources (`Douglas contractor_lien`, `Maricopa contractor_lien`, `Palm
Beach contractor_lien`/`tax_lien`) currently fail via Web-Use navigation/tool
gaps — see
[CursorTouch/Web-Use#20](https://github.com/CursorTouch/Web-Use/issues/20)
(`menu_tool`/`upload_tool`/`human_tool` implemented but missing from
`BUILTIN_TOOLS`). This is being fixed upstream independently of this
dashboard. The Overview page's failure-reason chart and a dedicated banner
(catalog #40) should surface this as a known, tracked blocker rather than an
unexplained failure rate.

## Feature Catalog (40 Improvements)

Full pool of improvement ideas, grouped by area. **`[v1]`** marks what's in
the initial build (10 items, corresponding to the task breakdown below); the
rest is backlog for future iterations.

### A. Data Visualization & Analytics
1. `[v1]` KPI overview cards (liens today/week/month, active counties, last run status)
2. `[v1]` New-liens trend line chart per county over time (Recharts)
3. `[v1]` Failure-reason breakdown bar chart (`invalid_json`/`max_steps_exhausted`/`agent_aborted`/`subprocess_error`)
4. Per-source success-rate heatmap (county × source_kind, colored by recent success %)
5. Lien-amount distribution histogram (spot outlier/high-value liens)
6. Geographic map view of parcels (pin per lien, geocoded from `property_address`)
7. Step-budget analytics per source (avg steps used vs. `max_steps`, to right-size budgets like Douglas's)
8. Run duration analytics per county/source over time

### B. Run Management & Automation
9. `[v1]` Live log tail during a triggered run (SSE)
10. `[v1]` One-click "run all" / "run county" trigger buttons
11. `[v1]` Run history list with expandable per-source detail
12. Re-run a single failed source without re-running the whole county
13. `[v1]` Run concurrency lock + "run in progress" indicator
14. Cron visibility: show next scheduled fire time and whether the daily job is currently armed (surfaces the `CronCreate` 7-day-expiry caveat from `.ralph/agent/decisions.md` DEC-001)
15. Run diffing: compare two runs side by side
16. Auto-retry once on `subprocess_error`/timeout before marking a source failed

### C. Configuration & County Management
17. `[v1]` Read-only county config viewer (structured cards, not raw YAML)
18. In-UI YAML editing for existing counties (sources, prompts, `max_steps`, `min_lien_amount`)
19. "Add a new county" guided wizard (instead of hand-writing YAML)
20. Config validation preview before saving (mirrors `load_counties`' expectations)
21. Config version history / diff view (git-backed)
22. Prompt-tuning sandbox: test an `extract_prompt` against a URL without touching the real ledger

### D. Data Quality & Ledger Management
23. `[v1]` Filterable/sortable ledger table (county, source, date range, amount)
24. CSV/PDF export of filtered ledger views
25. Duplicate/near-duplicate review queue (rows caught by the `row_key` fallback hash)
26. Manual row annotation ("not relevant") without deleting the row
27. Ledger integrity checker (validate CSV schema matches `LEDGER_FIELDS`, flag drift)
28. "New since last visit" indicator

### E. Alerting & Notifications
29. In-dashboard mirror of the `PushNotification` summary already sent
30. Slack/webhook alert option alongside push notifications
31. Configurable alert thresholds (e.g. only notify above a `lien_amount`, or after N consecutive failures)
32. Weekly digest option instead of daily-only notification

### F. AI/Chat Agent Enhancements
33. `[v1]` Persistent docked Gemini chat panel — read-only data tools + propose-then-confirm config/run actions
34. "Explain this failure" button next to any failed source (pre-fills a chat question with that row's context)
35. Chat memory across sessions
36. Chat-suggested `extract_prompt` rewrites when a source repeatedly fails `invalid_json`

### G. Collaboration & Ops Tooling
37. Dark mode toggle (the Data-Dense Dashboard style explicitly supports both)
38. Keyboard shortcuts for power users (e.g. `r` to trigger a run, `/` to focus chat)
39. Audit log of every config change and manually-triggered run (who/when/what)
40. Known-issues banner surfacing tracked external blockers (e.g. linking Web-Use#20) instead of raw unexplained failures

## v1 Task Breakdown

Corresponds to `.ralph/tasks/dashboard/task-01..08`:

1. Next.js scaffold + Tailwind/shadcn + design tokens + sidebar shell
2. Data layer (`lib/data.ts`: ledger CSV parser, county YAML loader, `runs.jsonl` reader/writer)
3. Overview page (catalog #1, #2, #3)
4. Liens page (catalog #23)
5. Runs page + trigger API + SSE + concurrency lock (catalog #9, #10, #11, #13)
6. Counties page (catalog #17)
7. Chat agent — Gemini integration, tools, docked panel (catalog #33)
8. Testing pass + manual e2e walkthrough + polish
