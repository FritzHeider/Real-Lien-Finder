# Plan

1. Step 1 - County config schema (Maricopa AZ) — **COMPLETED**
   - Demo: `scripts/lien_prospecting/counties/maricopa_az.yaml` parses via the mandated
     `uv run python -c "import yaml; ..."` command and matches the design doc's schema.
   - Wave: single task, closed. Verified by Fresh-Eyes Critic + Finalizer, commit 52a765c
     (plus the pyproject.toml fix in the same commit).

2. Step 2 - Remaining county configs (Palm Beach FL + Douglas CO) — **COMPLETED**
   - Demo: both new YAML files parse with the same schema as Maricopa and their
     `dedup_key` fields are all present in their own `extract_prompt` text.
   - Wave: one task per county file (2 tasks), each independently verifiable. Both closed;
     bookkeeping (code-task.md frontmatter + runtime tasks) fixed and re-verified.

3. Step 3 - run.py extraction (load configs, template prompt, shell out to Web-Use CLI,
   parse JSON response with regex fallback) — **CURRENT**
   - Demo: running `run.py` against one county with a stubbed/mocked Web-Use call produces
     parsed JSON rows or a `failed: invalid_json` marker.
   - Prerequisite verified: `../Web-Use` exists, has `src/cli.py`, and `.env` has a non-empty
     key the provider will use (`GEMINI_API_KEY`, which Web-Use's `ChatGoogle` checks before
     falling back to `GOOGLE_API_KEY` — see flagged deviation in context.md). Not a blocker.
   - Wave (sequential, single file `scripts/lien_prospecting/run.py`):
     1. `step-03:scaffold-and-config-loading` — `resolve_web_use_dir()` (AC#6),
        `load_counties()`, `build_prompt()`.
     2. `step-03:run-extraction-happy-and-fallback` — `run_extraction()` happy path + regex
        fallback (AC#1, AC#2).
     3. `step-03:run-extraction-error-handling` — timeout/non-zero exit, missing marker,
        unparsable JSON (AC#3, AC#5).
     4. `step-03:min-lien-amount-filter` — `apply_min_lien_amount()` (AC#4).

4. Step 4 - run.py ledger (dedup against per-county CSV, append genuinely-new rows)
   - Demo: running the ledger diff logic twice against the same parsed rows adds rows once,
     not twice.
   - Wave: TBD.

5. Step 5 - run.py error handling + summary accumulation (subprocess timeout, max-steps
   exhaustion, per-source failure isolation)
   - Demo: a simulated subprocess timeout/crash for one source does not stop other sources
     or counties from running.
   - Wave: TBD.

6. Step 6 - Summary output contract (`SUMMARY_JSON:` line, `quiet` flag, exit-0 behavior)
   - Demo: `run.py`'s stdout ends with a well-formed `SUMMARY_JSON: {...}` line whose shape
     matches the design doc, `quiet: true` only when zero new rows and zero failures.
   - Wave: TBD.

7. Step 7 - `.claude/skills/lien-prospecting/SKILL.md`
   - Demo: skill doc explains schema, ad-hoc usage, adding a county, `WEB_USE_DIR`
     prerequisite, and the required `PushNotification` follow-up.
   - Wave: TBD.

8. Step 8 - Scheduling + end-to-end validation
   - Demo: a real run across all 3 counties, a real cron entry via `/schedule`, everything
     committed.
   - Wave: TBD.
