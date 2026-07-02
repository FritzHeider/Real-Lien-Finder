# Progress

## Current Step
Step 3 - run.py extraction stage
Spec: `.ralph/tasks/lien-prospecting/task-03-run-py-extraction.code-task.md`
Depends on: Step 1 (complete — real config to test against). Prerequisite (Web-Use checkout)
verified present and usable — see context.md "Flagged deviation" note (`.env` has
`GEMINI_API_KEY`, not the literally-named `GOOGLE_API_KEY`, but Web-Use's provider checks
`GEMINI_API_KEY` first, so this is not a blocker).

## Active Wave
Sequential chain, all in `scripts/lien_prospecting/run.py` (single file):
1. `task-1782957184-efbd` (key: `code-assist:lien-prospecting:step-03:scaffold-and-config-loading`) — status: open, READY. `resolve_web_use_dir()` + `load_counties()` + `build_prompt()`, AC#6.
2. `task-1782957184-ffa1` (key: `code-assist:lien-prospecting:step-03:run-extraction-happy-and-fallback`) — status: open, blocked_by #1. `run_extraction()` happy path + regex fallback, AC#1/AC#2.
3. `task-1782957184-75e3` (key: `code-assist:lien-prospecting:step-03:run-extraction-error-handling`) — status: open, blocked_by #2. Error branches (subprocess_error/max_steps_exhausted/invalid_json), AC#3/AC#5.
4. `task-1782957184-c7cb` (key: `code-assist:lien-prospecting:step-03:min-lien-amount-filter`) — status: open, blocked_by #3. `apply_min_lien_amount()`, AC#4.

Publishing `tasks.ready` for `task-1782957184-efbd` (only unblocked task in the wave).

## Verification Notes
- `task-1782957184-efbd`: initial pass content-correct but rejected by Fresh-Eyes Critic —
  `test_defaults_to_sibling_web_use_dir_when_env_unset` relied on the real `../Web-Use`
  sibling checkout on the dev machine instead of mocking, so it would raise uncaught on a
  fresh clone/CI runner. Fixed by building a fake `Web-Use/src/cli.py` under `tmp_path` and
  `monkeypatch.setattr(run, "PROJECT_ROOT", fake_project_root)` instead. Re-verified
  hermeticity by running the same assertions in a standalone script with `WEB_USE_DIR`
  unset and no reliance on any real sibling directory — passes. Full suite:
  `uv run pytest tests/test_lien_prospecting.py -v` — 6 passed. Commit: dc8db39.

## Completed Steps

### Step 1 - County config schema (Maricopa AZ)
- Task: `task-01-county-config-schema.code-task.md`, status: completed in frontmatter.
- `maricopa_az.yaml` verified against design schema; both acceptance criteria pass with the
  mandated `uv run python -c "import yaml; ..."` command.
- Required an unplanned fix: repo had no root `pyproject.toml`, so `uv run` couldn't find
  `pyyaml` even though system Python had it. Fixed by adding `pyproject.toml` (pyyaml>=6.0,
  requires-python >=3.11); `uv.lock` committed, `.venv/` already gitignored.
- Commit: 52a765c. Closed by Finalizer after independent re-verification.

### Step 2 - Remaining county configs (Palm Beach FL + Douglas CO)
- Task: `task-02-remaining-county-configs.code-task.md`, status: completed in frontmatter.
- `palm_beach_fl.yaml` and `douglas_co.yaml` verified against design schema; both parse,
  both have well-formed sources, all dedup_key fields present in extract_prompt text.
- Required an unplanned fix: task-lifecycle bookkeeping (code-task.md frontmatter, runtime
  task closure) was skipped on first pass despite content being correct — Fresh-Eyes Critic
  rejected, Builder fixed, Finalizer independently re-verified both content and bookkeeping.
- Commit: 45918be (content) + bookkeeping fix. Runtime tasks task-1782956776-3da7/-5b5e
  both closed.
