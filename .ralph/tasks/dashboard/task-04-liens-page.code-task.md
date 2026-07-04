---
status: pending
created: 2026-07-04
---
# Task: Liens Page (Filterable/Sortable Ledger Table)

## Description
Build the `/liens` page: a filterable, sortable table aggregating every
county's ledger CSV. Implements catalog item #23.

## Background
Fourth task of the dashboard feature. This is the primary "look at the actual
data" page — the ledger CSVs are the whole point of the pipeline.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` ("Pages & Layout" → `/liens`,
  "Design System" for table density/typography guidance)
- `scripts/lien_prospecting/run.py`'s `LEDGER_FIELDS` for the exact column
  set.

## Technical Requirements
1. A data table (shadcn/ui `Table` or a headless table lib) listing all
   `LEDGER_FIELDS` columns across every county's ledger, with a `county`
   column added (derived from which CSV the row came from — not itself an
   `LEDGER_FIELDS` entry).
2. Filters: county (multi-select), source kind (`tax_lien`/`contractor_lien`),
   date range (on `first_seen`), minimum `lien_amount`.
3. Sortable columns, at minimum `first_seen` and `lien_amount`.
4. `lien_amount` and other numeric columns use tabular/monospaced figures
   (Fira Code) per the design system, so columns of numbers align.
5. Empty state when a filter combination matches zero rows ("no liens match
   these filters" + a clear-filters action), not a blank table.
6. Data comes from `getLedgerRows()` (task 2) — no direct CSV access in this
   page.

## Dependencies
- Task 2 (`task-02-data-layer.code-task.md`)

## Implementation Approach
1. Build the table component consuming `getLedgerRows()`.
2. Add filter controls (shadcn/ui `Select`, date range picker, numeric input)
   wired to client-side filtering (dataset size is small — no need for
   server-side pagination in v1).
3. Wire column sorting.
4. Verify against this repo's real ledger CSVs (`douglas_co.csv`,
   `palm_beach_fl.csv`, and any `maricopa_az.csv` present).

## Acceptance Criteria

1. **All ledger rows aggregated correctly**
   - Given the real per-county ledger CSVs in this repo
   - When loading `/liens` with no filters applied
   - Then every row from every ledger CSV appears, each correctly tagged with
     its source county

2. **Filters narrow the result set correctly**
   - Given rows spanning multiple counties/source kinds/dates/amounts
   - When applying a county filter, a source-kind filter, a date range, and a
     minimum amount (individually and combined)
   - Then only matching rows are shown in each case

3. **Sorting works on numeric and date columns**
   - Given unsorted rows
   - When sorting by `lien_amount` or `first_seen`
   - Then rows reorder correctly ascending/descending

4. **Empty filter result shows a clear empty state**
   - Given a filter combination matching zero rows
   - When applied
   - Then a "no results" message with a way to clear filters is shown, not a
     blank table

## Metadata
- **Complexity**: Medium
- **Labels**: dashboard, table, liens-page
- **Required Skills**: React, table/filtering UI, Tailwind
