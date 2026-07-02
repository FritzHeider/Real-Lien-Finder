---
status: completed
created: 2026-07-01
started: 2026-07-02
completed: 2026-07-02
---
# Task: run.py — Ledger Diff & Append

## Description
Implement the per-county ledger: loading existing state, deduping newly-extracted rows against it, and appending genuinely-new rows with a `first_seen` date.

## Background
Each county gets its own persistent CSV ledger so that re-running the extraction (Task 3) doesn't re-flag the same lien as "new" every day. Correctness here matters directly — a bad dedup key means either duplicate spam or silently missed leads, either of which defeats the point of the feature.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "Driver Script (run.py)" step 5 and "Ledger CSV Schema")

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. `load_ledger(path: Path) -> list[dict]`: if `path` exists, read it as CSV and return a list of row dicts; if it doesn't exist, return `[]`.
2. `row_key(row: dict, dedup_key: list[str]) -> str`: if any field named in `dedup_key` is present and non-empty in `row`, build the key from those field(s) (joined deterministically, e.g. `"|".join(str(row[k]) for k in dedup_key if row.get(k))`). If none of the `dedup_key` fields are present/non-empty, fall back to `hashlib.sha1` of the concatenation of `(owner_name, property_address, filing_date)`.
3. `diff_new_rows(parsed_rows: list[dict], existing_rows: list[dict], dedup_key: list[str]) -> list[dict]`: compute `row_key` for every existing row into a set, then return only the `parsed_rows` whose `row_key` is not in that set.
4. `append_ledger(path: Path, new_rows: list[dict], source_kind: str, source_url: str, run_date: str) -> None`: write `new_rows` to the CSV at `path`. If the file doesn't exist, create it with the header `first_seen, source_kind, parcel_number, document_number, owner_name, property_address, lien_amount, filing_date, source_url` (exact column order per the design doc's Ledger CSV Schema). Set `first_seen=run_date` and `source_kind`/`source_url` from the function arguments on every appended row; fill any missing lien fields with empty strings rather than raising `KeyError`.

## Dependencies
- Task 3 (`task-03-run-py-extraction.code-task.md`) — this task operates on the row shape (list of dicts) that extraction produces.

## Implementation Approach
1. Add the four functions to `scripts/lien_prospecting/run.py` (same file as Task 3).
2. Extend `tests/test_lien_prospecting.py` with ledger-specific tests using `tmp_path` (pytest fixture) for isolated CSV files — do not write to the real `scripts/lien_prospecting/ledger/` directory during tests.

## Acceptance Criteria

1. **Fresh ledger creation**
   - Given no ledger CSV exists at `path`
   - When `append_ledger(path, new_rows, ...)` is called with one or more rows
   - Then the file is created with the correct header row and the given rows correctly populated

2. **Re-run doesn't duplicate**
   - Given a ledger CSV already containing a row with `parcel_number="123"`
   - When `parsed_rows` from a later run also contains a row with `parcel_number="123"`, and `diff_new_rows` is called against the loaded ledger
   - Then that row is excluded from the returned new-rows list

3. **Fallback dedup key is deterministic**
   - Given two rows missing both `parcel_number` and `document_number` but sharing identical `owner_name`, `property_address`, and `filing_date`
   - When `row_key` is computed for each
   - Then both produce the exact same key string

4. **Missing lien fields don't crash the append**
   - Given a parsed row missing `lien_amount` entirely
   - When `append_ledger` is called with it
   - Then the row is written with an empty string for `lien_amount` rather than raising

## Metadata
- **Complexity**: Medium
- **Labels**: python, csv, lien-prospecting, dedup
- **Required Skills**: Python, csv module, hashlib, pytest fixtures (tmp_path)
