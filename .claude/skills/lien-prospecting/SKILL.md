---
name: lien-prospecting
description: Use when asked to run lien prospecting, check for new tax/contractor liens, or add a county to the lien-watch list.
---

# Lien Prospecting

## Overview
This project runs a daily-ledger watch for newly-recorded tax and contractor
liens across a growing list of counties, looking for homeowners who might be
motivated to sell. Per-county extraction dogfoods the Web-Use browsing agent
(a sibling project) to read each county portal; `run.py` owns everything
deterministic — JSON parsing, `min_lien_amount` filtering, and ledger
dedup/append.

## Prerequisite
A Web-Use checkout must be available. Defaults to `../Web-Use` (a sibling
directory of this project); override with the `WEB_USE_DIR` environment
variable. It must contain `src/cli.py` and a working `.env` with
`GOOGLE_API_KEY`.

## Ad-hoc Usage
Run every configured county:
```bash
uv run python scripts/lien_prospecting/run.py
```

Run a single county by slug (the YAML filename without `.yaml`):
```bash
uv run python scripts/lien_prospecting/run.py --county maricopa_az
```

The process always exits `0` — per-source failures (blocked sites, invalid
JSON, timeouts) are captured in the summary, not raised as errors.

## Adding a County
Drop a new YAML file into `scripts/lien_prospecting/counties/` — no code
change required. Schema (see `maricopa_az.yaml` for a full example):

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

## Where Results Live
- `scripts/lien_prospecting/ledger/<slug>.csv` — one ledger per county,
  appended with genuinely-new rows only (gitignored, persists between runs).
- `scripts/lien_prospecting/run.log` — failure details (county, url, reason)
  for any source that didn't produce usable data (gitignored).

## Required Follow-up: Push Notification
`run.py` cannot send notifications itself — it's a plain subprocess with no
access to Claude Code's tool layer. After it finishes:

1. Read the **last line** of its stdout: `SUMMARY_JSON: {...}`.
2. Parse the JSON. Shape: `{"counties": {<slug>: {"new": int, "failed_sources": [...]}}, "quiet": bool}`.
3. If `quiet` is `true`, skip the notification — zero new liens and zero
   failures across every county.
4. Otherwise call `PushNotification` with a human-readable summary: total new
   liens, a per-county breakdown, and any failed sources.
