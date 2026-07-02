# Context: Lien Prospecting

## Source
8 self-contained `.code-task.md` files under `.ralph/tasks/lien-prospecting/`, executed in
strict order per the master prompt. Each file is its own spec (description, requirements,
acceptance criteria). This directory tracks step-wave queue state on top of that existing
per-task structure — it does not replace the task files.

## Required reading
- `.ralph/specs/lien-prospecting/design.md` — full design spec (schema, run.py flow, ledger
  CSV schema, error handling table, skill/scheduling contract).

## Repo patterns discovered so far
- No pre-existing Python package structure; `scripts/lien_prospecting/counties/*.yaml` is a
  flat directory of per-county configs, one file each.
- Root `pyproject.toml` (added in task-01 fix) declares `pyyaml>=6.0`, `requires-python >=3.11`.
  All Python validation must go through `uv run python ...` (never bare `python3`) — see
  memory mem-1782956588-6fba / mem-1782956633-c1c4: bare `python3` masks missing deps because
  system Python has pyyaml installed but `uv run`'s isolated env does not unless declared in
  pyproject.toml.
- County YAML schema (established by task-01, `maricopa_az.yaml`):
  ```yaml
  name: "<County Name, ST>"
  lookback_days: 7
  min_lien_amount: null
  sources:
    - kind: tax_lien | contractor_lien
      url: "https://..."
      extract_prompt: >
        ...must contain the literal `{lookback_days}` placeholder...
        Return ONLY a JSON array of objects with those exact keys, no prose.
  dedup_key: ["field_a", "field_b"]
  ```
- Validation command (mandated, must be run exactly like this):
  `uv run python -c "import yaml; print(yaml.safe_load(open('scripts/lien_prospecting/counties/<file>.yaml')))"`

## Integration points
- `run.py` (tasks 3-6) will load every YAML in `counties/` uniformly — schema consistency
  across county files is a hard requirement, not a style preference.
- Web-Use dependency (`WEB_USE_DIR`, default `../Web-Use`) only matters starting Task 3.

## Global constraints (apply to every step)
- Files under 500 lines.
- Validate input at system boundaries.
- Never commit `.env`, ledger CSVs, `run.log` (gitignore already covers; extend if new
  runtime-state paths appear).
- `uv run` for all Python execution, including Web-Use's `src/cli.py` (cwd=WEB_USE_DIR).
- No vendoring/copying Web-Use code.

## Step 2 acceptance criteria (completed, task-02)
1. `palm_beach_fl.yaml` and `douglas_co.yaml` each parse via `yaml.safe_load` and contain
   `name`, `lookback_days`, `min_lien_amount`, `sources` (non-empty list of
   `{kind, url, extract_prompt}`), `dedup_key`.
2. For each county, every field name in `dedup_key` appears as a requested field in at least
   one of that county's `extract_prompt` strings.
3. Both files use identical field structure/key names to `maricopa_az.yaml`.

## Flagged deviation — Web-Use prerequisite env var name (Step 3 start)
Master prompt's Prerequisite section says the Web-Use `.env` must have `GOOGLE_API_KEY`.
Checked `../Web-Use/.env` directly: it has `GEMINI_API_KEY` set (non-empty, 53 chars), not
`GOOGLE_API_KEY`. Read `../Web-Use/src/providers/google/llm.py:50` — the actual provider
does `os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")`, i.e. it checks
`GEMINI_API_KEY` first. So the checkout is genuinely usable as-is; this is a naming mismatch
in the master prompt/prerequisite text (and in Web-Use's own SKILL.md, which also only
mentions `GOOGLE_API_KEY`), not a real blocker. Not stopping — flagging per the master
prompt's "say so and propose the fix" instruction. No action needed unless a real auth
failure is observed during Step 3/8 execution.

## Step 3 scope (task-03: run.py extraction stage)
Spec: `.ralph/tasks/lien-prospecting/task-03-run-py-extraction.code-task.md`.
Builds `scripts/lien_prospecting/run.py` with four functions (ledger/main-loop logic is
explicitly out of scope — Task 4+):
- `resolve_web_use_dir() -> Path` — env var `WEB_USE_DIR` or `../Web-Use` default; raise
  loudly at startup if `src/cli.py` isn't found there (AC#6).
- `load_counties(counties_dir) -> list[dict]` — parse every `*.yaml` in
  `scripts/lien_prospecting/counties/`, tagging each with source filename/slug.
- `build_prompt(source, lookback_days) -> str` — format `{lookback_days}` into
  `source["extract_prompt"]`.
- `run_extraction(county_name, source, lookback_days, web_use_dir) -> tuple[list[dict]|None, str|None]`
  — shells out to `uv run python src/cli.py --query ... --headless --steps 40` with
  `cwd=web_use_dir`, `timeout=300`; parses stdout after `[+] Final Agent Response:`, direct
  `json.loads` then regex `[...]` fallback; failure reasons: `subprocess_error` (timeout/
  non-zero exit), `invalid_json` (marker present but unparsable), `max_steps_exhausted`
  (marker absent entirely).
- `apply_min_lien_amount(rows, min_amount) -> list[dict]` — filters by numeric
  `lien_amount >= min_amount`; non-numeric/missing `lien_amount` rows are kept, not dropped.
Tests go in `tests/test_lien_prospecting.py`, mocking `subprocess.run` — no real
browser/LLM calls in this step's tests. Run via `uv run pytest tests/test_lien_prospecting.py -v`.
`run.py` must stay importable with no top-level execution side effects beyond an
`if __name__ == "__main__":` guard (later steps add the real CLI entry point).
