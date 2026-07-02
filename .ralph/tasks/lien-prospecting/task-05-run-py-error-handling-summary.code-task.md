---
status: pending
created: 2026-07-01
started: null
completed: null
---
# Task: run.py — Error Handling & Run Summary

## Description
Wire extraction (Task 3) and ledger (Task 4) into a full per-county, per-source loop that never hard-fails, and produces a structured run summary.

## Background
This is a daily unattended job. One county's site being down, blocked, or having changed layout must not prevent the other counties from being checked, and must not crash the process — the design requires failures to be surfaced through reporting, not through process failure.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "Driver Script (run.py)" steps 6-9 and "Error Handling" table)

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. `run_county(county_config: dict, web_use_dir: Path) -> dict`: for each `source` in `county_config["sources"]`, call `run_extraction(..., web_use_dir=web_use_dir)` (Task 3). On failure (non-`None` failure reason), append `{"source_kind": ..., "url": ..., "reason": ...}` to a `failed_sources` list instead of raising. On success, run `apply_min_lien_amount`, then `diff_new_rows`/`append_ledger` (Task 4) against `ledger/<county_slug>.csv`, and add the count of newly-appended rows to a running `new` total for the county. Return `{"new": int, "failed_sources": list}`.
2. `main(counties_dir=..., ledger_dir=..., county_filter: str | None = None) -> dict`: resolve `web_use_dir` via `resolve_web_use_dir()` (Task 3) once, up front — let it raise immediately if misconfigured rather than catching it per-source. Load all counties via `load_counties` (Task 3), optionally filtered to a single county slug if `county_filter` is set, call `run_county` for each (passing `web_use_dir`), and accumulate `{county_name: {"new": N, "failed_sources": [...]}}`. For every failure encountered, append a line to `scripts/lien_prospecting/run.log` containing the county, source URL, failure reason, and (if available) a truncated snippet of the raw agent output. Return the accumulated summary dict.
3. Add a CLI entry point (`argparse`) supporting `--county <slug>` (maps to `county_filter`, matching the county YAML's filename stem) to scope a run to one county.
4. `if __name__ == "__main__":` block: call `main()` with parsed CLI args, print the resulting summary (Task 6 will replace/extend this with the `SUMMARY_JSON:` line), and always call `sys.exit(0)` regardless of any failures recorded in the summary.

## Dependencies
- Task 4 (`task-04-run-py-ledger.code-task.md`)

## Implementation Approach
1. Add `run_county`, `main`, and the `argparse`-based CLI entry point to `scripts/lien_prospecting/run.py`.
2. Extend `tests/test_lien_prospecting.py`: mock `run_extraction` directly (rather than `subprocess.run`) for these higher-level tests to keep them fast and focused on control flow, not the extraction internals already covered in Task 3's tests.

## Acceptance Criteria

1. **One county's failure doesn't stop others**
   - Given 3 counties where county 2's only source's `run_extraction` call returns `(None, "invalid_json")` and the other two counties' calls succeed normally
   - When `main()` runs across all three
   - Then counties 1 and 3 report their normal new-row counts, and county 2's entry shows `"new": 0` and a non-empty `failed_sources` list

2. **Process always exits 0**
   - Given any mix of successes and failures across counties (including a county where every source fails)
   - When `scripts/lien_prospecting/run.py` is executed as a script via subprocess
   - Then the process exit code is 0

3. **`--county` flag scopes to one county**
   - Given the `--county maricopa_az` flag and 3 available county configs
   - When `run.py` is executed with that flag
   - Then only `maricopa_az`'s sources are processed, and the returned/printed summary contains only that county's key

4. **Failures are logged with enough detail to debug**
   - Given a source failure with reason `"invalid_json"`
   - When `main()` completes
   - Then `run.log` contains a line identifying the county, the failing source's URL, and the failure reason

## Metadata
- **Complexity**: Medium
- **Labels**: python, error-handling, lien-prospecting, cli
- **Required Skills**: Python, argparse, logging, unit testing
