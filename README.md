# Real-Lien-Finder

A daily-automated, config-driven watch for newly-recorded tax and contractor
liens across a growing list of counties — surfacing homeowners who might be
motivated to sell.

Per-county extraction dogfoods the [Web-Use](../Web-Use) browsing agent (a
sibling project) to read each county's public records portal. `run.py` owns
everything deterministic: JSON parsing of the agent's output, `min_lien_amount`
filtering, and ledger dedup/append — none of that is left to model judgment.

## Prerequisite

A Web-Use checkout must be available, containing `src/cli.py` and a working
`.env` with a Gemini API key. Defaults to `../Web-Use` (a sibling directory of
this project); override with the `WEB_USE_DIR` environment variable.

## Usage

Run every configured county:

```bash
uv run python scripts/lien_prospecting/run.py
```

Run a single county by slug (the YAML filename without `.yaml`):

```bash
uv run python scripts/lien_prospecting/run.py --county maricopa_az
```

The process always exits `0` — per-source failures (blocked sites, invalid
JSON, browser crashes, timeouts) are captured in the run summary rather than
raised as errors. The last line of stdout is a machine-readable summary:

```
SUMMARY_JSON: {"counties": {<name>: {"new": int, "failed_sources": [...]}}, "quiet": bool}
```

## Adding a County

Drop a new YAML file into `scripts/lien_prospecting/counties/` — no code
change required:

```yaml
name: "County, ST"           # display name
lookback_days: 7             # how far back sources should search
min_lien_amount: null        # e.g. 1000 to ignore small liens; null = no filter
sources:
  - kind: tax_lien           # or contractor_lien
    url: "https://..."       # portal the agent starts from
    extract_prompt: >        # templated with {lookback_days}; must instruct
      ...                    # the agent to return ONLY a JSON array
dedup_key: ["parcel_number", "document_number"]  # fields identifying a unique lien
```

See `scripts/lien_prospecting/counties/maricopa_az.yaml` for a full example.

## Where Results Live

- `scripts/lien_prospecting/ledger/<slug>.csv` — one ledger per county,
  appended with genuinely-new rows only (gitignored, persists between runs).
- `scripts/lien_prospecting/run.log` — failure details (county, url, reason)
  for any source that didn't produce usable data (gitignored).

### Failure reasons

| Reason | Meaning |
|---|---|
| `invalid_json` | Agent's final response wasn't parseable JSON (portal layout changed, no data found, etc). |
| `max_steps_exhausted` | Agent hit its step budget before completing — often a portal whose navigation is too deep/complex for the step limit. |
| `agent_aborted` | Browser/session crashed mid-run (e.g. a dropped DevTools connection) after repeated tool failures. |
| `subprocess_error` | The Web-Use subprocess timed out or exited non-zero. |

## Scheduling

The daily run is driven by a scheduled agent that invokes the
`.claude/skills/lien-prospecting/SKILL.md` skill, parses the run's
`SUMMARY_JSON` line, and sends a push notification unless the run was quiet
(zero new liens, zero failures). See that skill file for the exact contract.

## Development

```bash
uv run pytest tests/ -q
```

Keep files under 500 lines. Never commit `.env`, ledger CSVs, or `run.log` —
see `.gitignore`.
