---
status: in_progress
created: 2026-07-01
started: 2026-07-02
completed: null
---
# Task: run.py — Extraction Stage

## Description
Implement the extraction stage of `scripts/lien_prospecting/run.py`: load county configs, drive the Web-Use agent (`src/cli.py`, a separate sibling repo) per source, and parse its output into structured JSON rows.

## Background
This is a standalone project, not a subfolder of Web-Use. Its extraction step shells out to Web-Use's `src/cli.py` (`--query`, `--headless`, `--steps`; requires `GOOGLE_API_KEY` in Web-Use's `.env`) by running the subprocess with `cwd` set to the Web-Use repo path — see the design doc's "External Dependency: Web-Use" section for the `WEB_USE_DIR` resolution rule (env var, default `../Web-Use` sibling checkout). This task builds the piece that calls it programmatically per county/source and turns its freeform final answer into structured data. Ledger diffing is explicitly NOT part of this task (see Task 4).

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "External Dependency: Web-Use" and "Driver Script (run.py)" steps 1-4)

**Additional References:**
- `<WEB_USE_DIR>/.claude/skills/web-use-agent/SKILL.md` — the CLI contract this task's subprocess calls must follow (read this from the Web-Use checkout, e.g. `../Web-Use/.claude/skills/web-use-agent/SKILL.md`)
- `scripts/lien_prospecting/counties/maricopa_az.yaml` (from Task 1) — a real config to test against

**Note:** Read the design document before beginning implementation.

## Technical Requirements
0. `resolve_web_use_dir() -> Path`: read the `WEB_USE_DIR` environment variable; if unset, default to `../Web-Use` resolved relative to this project's root. Raise a clear error at startup (not deep inside a subprocess call) if the resolved path doesn't contain `src/cli.py`, so a missing/misconfigured Web-Use checkout fails loudly instead of producing confusing `subprocess_error` results for every source.
1. `load_counties(counties_dir: Path) -> list[dict]`: load and parse every `*.yaml` file in `scripts/lien_prospecting/counties/`, returning the parsed config dicts (include the source filename/slug in each returned dict for later use).
2. `build_prompt(source: dict, lookback_days: int) -> str`: format `source["extract_prompt"]` with `lookback_days` substituted for the `{lookback_days}` placeholder.
3. `run_extraction(county_name: str, source: dict, lookback_days: int, web_use_dir: Path) -> tuple[list[dict] | None, str | None]`:
   - Build the prompt via `build_prompt`, prepend/append the source's `url` as the agent's starting point if not already implied by the prompt.
   - Invoke `uv run python src/cli.py --query "<prompt>" --headless --steps 40` via `subprocess.run(..., cwd=web_use_dir, timeout=300, capture_output=True, text=True)` — `cwd` must be `web_use_dir` so `uv` resolves Web-Use's own `pyproject.toml`/venv, not this project's.
   - On `subprocess.TimeoutExpired` or non-zero exit code: return `(None, "subprocess_error")`.
   - Otherwise, extract the text following the literal line `[+] Final Agent Response:` from stdout.
   - Try `json.loads` on that text directly. On failure, regex-extract the first `[...]` block (`re.search(r'\[.*\]', text, re.DOTALL)`) and retry `json.loads` on the match.
   - If both attempts fail: return `(None, "invalid_json")`. If the raw output indicates the agent hit its step limit without a final answer (e.g. no `[+] Final Agent Response:` marker present at all), return `(None, "max_steps_exhausted")` instead.
   - On success: return `(parsed_rows, None)`.
4. `apply_min_lien_amount(rows: list[dict], min_amount: float | None) -> list[dict]`: if `min_amount` is `None`, return `rows` unchanged. Otherwise keep only rows whose `lien_amount` parses as a number `>= min_amount`; rows where `lien_amount` isn't numeric (missing, non-numeric string) are kept as-is (not filtered out) rather than crashing.

## Dependencies
- Task 1 (`task-01-county-config-schema.code-task.md`) — needs a real config file to test extraction against.

## Implementation Approach
1. Create `scripts/lien_prospecting/run.py` with the four functions above (ledger/main-loop logic comes in later tasks — this task should leave `run.py` importable with just these functions, no top-level execution side effects beyond `if __name__ == "__main__"` guard).
2. Create `tests/test_lien_prospecting.py` with `unittest.mock.patch("subprocess.run")` to simulate agent responses without hitting a real browser/LLM.
3. Run tests locally: `uv run pytest tests/test_lien_prospecting.py -v`.

## Acceptance Criteria

1. **Valid JSON parses cleanly**
   - Given a mocked `subprocess.run` whose stdout ends with `[+] Final Agent Response:\n[{"parcel_number": "123", "owner_name": "Jane Doe", "lien_amount": 500}]`
   - When `run_extraction` is called
   - Then it returns `([{"parcel_number": "123", ...}], None)`

2. **Malformed-but-recoverable output falls back to regex extraction**
   - Given a mocked subprocess whose stdout has prose text with an embedded JSON array (e.g. `"Here are the results:\n[{...}]\nLet me know if you need more."`)
   - When `run_extraction` is called
   - Then it successfully extracts and parses the array via the regex fallback, returning it with `None` as the failure reason

3. **Unparsable output is reported, not raised**
   - Given a mocked subprocess whose stdout has no JSON array anywhere and no `[+] Final Agent Response:` marker
   - When `run_extraction` is called
   - Then it returns `(None, "max_steps_exhausted")` without raising an exception

4. **min_lien_amount filters correctly and tolerates bad data**
   - Given rows `[{"lien_amount": 500}, {"lien_amount": 2000}, {"lien_amount": "unknown"}]`
   - When `apply_min_lien_amount(rows, 1000)` is called
   - Then the result contains the `2000` row and the `"unknown"` row, but not the `500` row

5. **Subprocess timeout is handled**
   - Given a mocked `subprocess.run` that raises `subprocess.TimeoutExpired`
   - When `run_extraction` is called
   - Then it returns `(None, "subprocess_error")` without raising

6. **Missing Web-Use checkout fails loudly at startup**
   - Given `WEB_USE_DIR` (or its `../Web-Use` default) does not contain `src/cli.py`
   - When `resolve_web_use_dir()` is called
   - Then it raises a clear, descriptive error immediately, rather than the failure surfacing later as an opaque `subprocess_error` on every source

## Metadata
- **Complexity**: Medium
- **Labels**: python, scraping, lien-prospecting, subprocess
- **Required Skills**: Python, subprocess, regex, unit testing with mocks
