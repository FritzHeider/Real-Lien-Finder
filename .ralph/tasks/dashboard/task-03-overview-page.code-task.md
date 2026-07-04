---
status: pending
created: 2026-07-04
---
# Task: Overview Page (KPIs, Trend Chart, Failure Breakdown)

## Description
Build the `/` Overview page: KPI cards, a new-liens trend line chart per
county, and a failure-reason breakdown bar chart. Implements catalog items
#1, #2, #3.

## Background
Third task of the dashboard feature. This is the landing page — the first
thing an operator sees, so it needs to answer "is everything okay?" at a
glance.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` ("Pages & Layout" → Overview,
  and "Design System" for chart guidance)

## Technical Requirements
1. KPI row: liens found today, liens found this week, count of active
   (configured) counties, and last run status (timestamp + quiet/not-quiet),
   derived from `getRunHistory()` and `getLedgerRows()`.
2. New-liens trend line chart (Recharts): one line per county, x-axis =
   `first_seen` date from ledger rows, y-axis = count. Per the design
   system's chart guidance — fewer than 4 data points for a county should
   fall back to a KPI-style note rather than an empty/misleading line.
3. Failure-reason breakdown: a bar chart (not pie) counting occurrences of
   each reason (`invalid_json`, `max_steps_exhausted`, `agent_aborted`,
   `subprocess_error`) across recent run history.
4. Empty states: if `runs.jsonl` has zero entries yet (dashboard freshly
   installed, no run triggered), show a clear "no runs yet — trigger one from
   the Runs page" message instead of blank/broken charts.
5. All data comes from `lib/data.ts` (task 2) — no direct file access in this
   page's components.

## Dependencies
- Task 2 (`task-02-data-layer.code-task.md`)

## Implementation Approach
1. Build KPI card components (shadcn/ui `Card`).
2. Wire Recharts `LineChart` and `BarChart` components using the design
   system's color tokens.
3. Handle the zero-data and sparse-data (< 4 points) empty/fallback states
   explicitly — don't let Recharts render a misleading chart on no data.
4. Manually verify against this repo's real `runs.jsonl` (once task 5 exists
   and at least one real run has been triggered) and real ledger CSVs.

## Acceptance Criteria

1. **KPI cards render real counts**
   - Given real ledger and run-history data
   - When loading `/`
   - Then the KPI row shows non-placeholder counts matching what
     `getLedgerRows()`/`getRunHistory()` actually return

2. **Trend chart reflects ledger data**
   - Given ledger rows across multiple `first_seen` dates for at least one
     county
   - When loading `/`
   - Then the trend chart plots one line per county with points at the
     correct dates/counts

3. **Failure breakdown reflects run history**
   - Given run history containing multiple failure reasons
   - When loading `/`
   - Then the bar chart shows one bar per distinct reason with an accurate
     count, and a legend/label identifies each (not color-only)

4. **Empty state instead of broken chart**
   - Given zero entries in `runs.jsonl`
   - When loading `/`
   - Then a clear empty-state message is shown instead of an empty/broken
     chart

## Metadata
- **Complexity**: Medium
- **Labels**: dashboard, charts, overview-page
- **Required Skills**: React, Recharts, Tailwind
