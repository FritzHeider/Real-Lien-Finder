# Design: Lien Prospecting

**Goal:** Find homeowners with newly-recorded tax or contractor liens who might be motivated to sell — a config-driven, daily-automated watch across a growing list of counties, dogfooding the Web-Use browsing agent (a separate sibling project) for the page-reading step.

## External Dependency: Web-Use

This project is standalone — it is not a subfolder of Web-Use — but its extraction step shells out to Web-Use's `src/cli.py`. `run.py` resolves the Web-Use repo path from the `WEB_USE_DIR` environment variable, defaulting to `../Web-Use` (i.e. a sibling checkout at the same directory level as this project). Every `subprocess.run` call to `uv run python src/cli.py` must set `cwd=WEB_USE_DIR` so `uv` picks up Web-Use's own `pyproject.toml`/venv — this project does not vendor or duplicate any of Web-Use's dependencies.

## Scope

- Generic multi-county technique: adding a county means adding a config file, not writing code.
- Starting counties (affluent submarkets, verified currently-active public portals):
  1. **Maricopa County, AZ** (Scottsdale, Paradise Valley, Fountain Hills) — tax lien auction at `maricopa.arizonataxsale.com`; recorder search at `recorder.maricopa.gov/recording/document-search.html`.
  2. **Palm Beach County, FL** (Palm Beach, Boca Raton, Jupiter) — tax deed sales at `taxdeed.mypalmbeachclerk.com`; Clerk & Comptroller Official Records search.
  3. **Douglas County, CO** (Castle Rock, Highlands Ranch, Parker) — tax lien sale via SRI's `zeusauction.com`; recorder search via `LandmarkWeb` (`apps.douglas.co.us/LandmarkWeb`).
- Output is lead data only (owner name, property address, lien facts) — no contact/skip-tracing in this scope.
- Runs daily via a single scheduled job that loops all configured counties.

## Architecture

```
scripts/lien_prospecting/
  counties/
    maricopa_az.yaml
    palm_beach_fl.yaml
    douglas_co.yaml
  ledger/               # gitignored — one CSV per county, persists between runs
    maricopa_az.csv
    palm_beach_fl.csv
    douglas_co.csv
  run.py                # driver: loop counties -> extract -> diff -> notify
.claude/skills/lien-prospecting/
  SKILL.md              # ad-hoc usage, config schema, how to add a county
```

Flow per run: `run.py` loads each county YAML → for each `source` in that county, builds an extraction prompt (with `{lookback_days}` templated in) and calls `uv run python src/cli.py --query "<prompt>" --headless --steps 40` with `cwd=WEB_USE_DIR` (see "External Dependency: Web-Use" above) → the agent's final answer is parsed as strict JSON → rows are filtered by `min_lien_amount` if set → diffed against that county's ledger CSV by `dedup_key` (or a fallback hash) → genuinely-new rows are appended with a `first_seen` date → after all counties, one push notification summarizes new-lien counts per county and any failed sources.

The **skill** documents the config schema and ad-hoc/add-a-county usage. The **scheduled job** (daily cron) just invokes the skill, which runs `run.py` for every configured county.

## County Config Schema

```yaml
# scripts/lien_prospecting/counties/maricopa_az.yaml
name: "Maricopa County, AZ"
lookback_days: 7
min_lien_amount: null   # e.g. 1000 to ignore small liens
sources:
  - kind: tax_lien
    url: "https://maricopa.arizonataxsale.com"
    extract_prompt: >
      Find tax liens sold/filed in the last {lookback_days} days. For each parcel,
      extract: parcel_number, owner_name, property_address, lien_amount,
      sale_or_filing_date. Return ONLY a JSON array of objects with those exact
      keys, no prose.
  - kind: contractor_lien
    url: "https://recorder.maricopa.gov/recording/document-search.html"
    extract_prompt: >
      Search recorded documents of type "Mechanic's Lien" filed in the last
      {lookback_days} days. For each result, extract: document_number,
      owner_name, property_address, lien_amount (if shown), filing_date.
      Return ONLY a JSON array, no prose.
dedup_key: ["parcel_number", "document_number"]
```

- `sources` lets a county have a tax-lien source, a contractor/mechanic's-lien source, or both.
- `extract_prompt` is templated (`{lookback_days}`) and fed into `src/cli.py --query`, with the source `url` as the agent's starting point.
- `dedup_key`: whichever of these fields is present per source uniquely identifies a lien; used to detect "new" rows on each run.
- `min_lien_amount` is enforced deterministically in `run.py` after parsing — never delegated to the LLM prompt, since numeric filtering isn't reliably enforced across every row by an LLM.
- `max_steps` (optional, per-source): overrides the default 40-step budget passed to `src/cli.py --steps`. **Deviation from original design**: the design originally hardcoded `--steps 40` for every source; added 2026-07-04 after live e2e testing showed Douglas's `contractor_lien` source (LandmarkWeb's disclaimer/menu navigation) exhausting 40 steps without reaching the search form. Defaults to 40 when absent, so existing configs are unaffected.

## Driver Script (`run.py`)

1. Load every YAML in `counties/`.
2. For each county, for each `source`: template the prompt, call Web-Use's `src/cli.py` via subprocess (`cwd=WEB_USE_DIR`) with a 5-minute timeout, capture the final answer text.
3. Parse as JSON: try `json.loads` directly, then fall back to regex-extracting the first `[...]` block. Failure → mark that source `failed: invalid_json` (or `failed: max_steps_exhausted` specifically when the agent ran out of steps without a done call) and continue — one bad source must not kill the run.
4. Apply `min_lien_amount` filter if set.
5. Load/create that county's ledger CSV. Diff parsed rows against existing rows by `dedup_key`; if a row is missing its dedup fields, fall back to a hash of `(owner_name, property_address, filing_date)` so it's never silently dropped or falsely re-flagged as new every run.
6. Append genuinely-new rows with a `first_seen` date.
7. Accumulate a summary: `{county: {new: N, failed_sources: [...]}}`.
8. After all counties, print the summary as a final `SUMMARY_JSON: {...}` line to stdout, plus `quiet: true` in the payload if there were zero new rows and zero failures across every county. **`run.py` does not send the push notification itself** — it's a plain subprocess with no access to Claude Code's tool layer. The invoking skill/agent reads this line and calls `PushNotification` (skipping the call when `quiet: true`).
9. Always exit 0 if the loop completed, even with some sources failed — failures are surfaced via the summary line, not via process failure (this is a daily unattended job; one bad county's site shouldn't fail the whole run).

## Ledger CSV Schema

One file per county at `ledger/<county_slug>.csv`:

| column | notes |
|---|---|
| `first_seen` | date this row was added to the ledger (run date) |
| `source_kind` | `tax_lien` / `contractor_lien` |
| `parcel_number` / `document_number` | whichever the source provides |
| `owner_name` | |
| `property_address` | |
| `lien_amount` | |
| `filing_date` | as reported by the county source |
| `source_url` | the portal URL it came from |

## Error Handling

| Failure mode | Handling |
|---|---|
| LLM final answer isn't valid JSON | `json.loads` → regex fallback → `failed: invalid_json`, raw output logged to `scripts/lien_prospecting/run.log`. |
| Agent can't find data / portal layout changed | Falls into the same `invalid_json` path; distinguishable via the logged raw text. |
| CAPTCHA / anti-bot block / agent exhausts steps | Logged specifically as `failed: max_steps_exhausted` (vs. generic `invalid_json`) so a blocked site is distinguishable from a prompt that needs tuning. No human-in-the-loop fallback — unattended daily run. Detected via stdout's "reached max steps" message, since Web-Use's `cli.py` still prints the final-response marker even when the agent hit its step budget without completing — marker presence alone isn't proof of a real result. |
| Browser/CDP session crash mid-run (e.g. "no close frame received or sent") | Web-Use's agent aborts after 3 consecutive tool failures and exits 0 with a stale final-response marker; detected via stdout's "aborted after N consecutive failures" message and logged as `failed: agent_aborted`, distinct from `invalid_json`, so a browser/session-layer crash isn't mistaken for a JSON-formatting problem. **Deviation from original design**: this failure mode/reason wasn't in the original table — added after live e2e testing surfaced it (2026-07-04) as a distinct, recurring cause on 2 of 3 counties' document-search sources. |
| Subprocess crash/hang | 5-minute timeout per source; timeout or non-zero exit → `failed: subprocess_error`. |
| Row missing `dedup_key` field(s) | Fallback hash of `(owner_name, property_address, filing_date)`. |

## Skill & Scheduling

- `.claude/skills/lien-prospecting/SKILL.md` (project-scoped, technique/reference type): documents what this does, the `WEB_USE_DIR` prerequisite (a Web-Use checkout available, default `../Web-Use`), how to run ad hoc (`uv run python scripts/lien_prospecting/run.py [--county <slug>]`), how to add a county (new YAML, no code change), where results live, how to read a failure summary, and the required follow-up step: parse the `SUMMARY_JSON:` line from `run.py`'s output and call `PushNotification` with a formatted summary (skip if `quiet: true`).
- One daily cron entry (via `/schedule`) whose prompt invokes the lien-prospecting skill; the skill runs `run.py` for all counties, then sends the push notification itself based on the printed summary.

## Out of Scope (this iteration)

- Contact/skip-tracing (owner phone/email/mailing address).
- Counties beyond the initial three (architecture supports adding more via config only).
- Any outbound contact/marketing automation.
