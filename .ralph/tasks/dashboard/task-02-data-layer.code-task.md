---
status: pending
created: 2026-07-04
---
# Task: Shared Data Layer (`lib/data.ts`)

## Description
Build the single set of server-side helpers that read the pipeline's on-disk
state — county YAMLs, ledger CSVs, and the dashboard's own `runs.jsonl` — so
every API route and the chat agent's read-only tools call the same parsing
code instead of each reimplementing it.

## Background
Second task of the dashboard feature. The dashboard is a pure reader/wrapper
around `run.py`'s existing files and output contract; this task is the
foundation every page (tasks 3-6) and the chat agent (task 7) depend on.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` ("Architecture" and "Data Flow"
  sections)
- Reference `scripts/lien_prospecting/run.py` for the exact shapes being
  parsed: `LEDGER_FIELDS` (ledger CSV columns), the county YAML schema
  (`load_counties`), and the `SUMMARY_JSON` payload shape
  (`build_summary_payload`).

**Note:** Read the design document and `run.py` before beginning
implementation — this task must stay byte-compatible with what `run.py`
actually produces, not a reinterpretation of it.

## Technical Requirements
1. `dashboard/lib/data.ts` (or a small module directory) exporting:
   - `getCounties(): CountyConfig[]` — parses every
     `scripts/lien_prospecting/counties/*.yaml`, mirroring `run.py`'s
     `load_counties` (tag each with its slug/filename).
   - `getLedgerRows(county?: string): LedgerRow[]` — parses
     `scripts/lien_prospecting/ledger/*.csv` using the `LEDGER_FIELDS` column
     set; optionally filtered to one county.
   - `getRunHistory(limit?: number): RunRecord[]` — reads
     `dashboard/.data/runs.jsonl` (one JSON object per line: `{timestamp,
     summary}`, where `summary` is exactly `run.py`'s `SUMMARY_JSON` payload
     shape), newest first.
   - `appendRunRecord(record: RunRecord): void` — appends one line to
     `runs.jsonl`, creating the file/directory if missing.
2. All parsers must validate at the boundary (per this project's global
   constraint): a malformed YAML file, a CSV row missing expected columns, or
   a bad JSON line in `runs.jsonl` is skipped with a logged warning, never
   thrown as an unhandled exception that crashes a page.
3. No filesystem access anywhere outside this module — API routes (tasks 3-7)
   must import from here, not read files directly.

## Dependencies
- Task 1 (`task-01-nextjs-scaffold.code-task.md`)

## Implementation Approach
1. Add a YAML parser (e.g. `js-yaml`) and CSV parser (e.g. `csv-parse`) as
   dependencies.
2. Implement each function against the real files already present in this
   repo (`scripts/lien_prospecting/counties/*.yaml`,
   `scripts/lien_prospecting/ledger/*.csv` — both exist today with real data
   from prior live runs).
3. Write unit tests (Vitest) covering: well-formed input, a missing file
   (returns empty, doesn't throw), a malformed row/line (skipped, not
   crashed), and `appendRunRecord` creating `dashboard/.data/` if absent.

## Acceptance Criteria

1. **County configs load correctly**
   - Given the 3 real county YAMLs in this repo
   - When calling `getCounties()`
   - Then it returns 3 entries with `name`, `sources`, `dedup_key` and a slug
     matching the filename stem

2. **Ledger rows parse and filter correctly**
   - Given the real ledger CSVs in `scripts/lien_prospecting/ledger/`
   - When calling `getLedgerRows()` and `getLedgerRows('douglas_co')`
   - Then the unfiltered call returns rows from all present ledgers and the
     filtered call returns only that county's rows

3. **Malformed input never crashes**
   - Given a temp directory with one well-formed and one malformed county
     YAML / ledger CSV row / `runs.jsonl` line
   - When calling the relevant getter
   - Then the well-formed data is returned, the malformed entry is skipped,
     and no exception propagates

4. **Run records round-trip**
   - Given a fresh temp `runs.jsonl` path (or the file absent)
   - When calling `appendRunRecord` twice then `getRunHistory()`
   - Then both records are returned, newest first

## Metadata
- **Complexity**: Medium
- **Labels**: data-layer, parsing, dashboard
- **Required Skills**: TypeScript, YAML/CSV parsing, Vitest
