---
status: pending
created: 2026-07-04
---
# Task: Counties Page (Read-Only Config Viewer)

## Description
Build the `/counties` page: a structured, read-only viewer of each county's
YAML config. Implements catalog item #17.

## Background
Sixth task of the dashboard feature. v1 is explicitly read-only here — in-UI
editing is backlog (catalog #18); this task must not add any way to write to
the county YAML files.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` ("Pages & Layout" → `/counties`,
  "Scope Decision")

## Technical Requirements
1. One card/section per county (from `getCounties()`, task 2) showing:
   `name`, `lookback_days`, `min_lien_amount`, and each `source` (`kind`,
   `url`, `extract_prompt`, `max_steps` if present — defaulting to 40 when
   absent, matching `run.py`'s `DEFAULT_MAX_STEPS`), and `dedup_key`.
2. Rendered as structured fields, not a raw YAML/JSON dump — e.g. the
   `extract_prompt` shown as readable multi-line text, `max_steps` and
   `lookback_days` as labeled values.
3. Strictly read-only: no form inputs, no save/edit actions, no API route
   that writes to `scripts/lien_prospecting/counties/*.yaml`.
4. If a county has zero sources or a missing optional field, render a
   sensible placeholder rather than an error.

## Dependencies
- Task 2 (`task-02-data-layer.code-task.md`)

## Implementation Approach
1. Build the county card component consuming `getCounties()`.
2. Verify against this repo's real 3 county YAMLs (`maricopa_az.yaml`,
   `douglas_co.yaml` — including its `max_steps: 80` override on
   `contractor_lien` — `palm_beach_fl.yaml`).

## Acceptance Criteria

1. **All counties render with correct fields**
   - Given the 3 real county YAMLs in this repo
   - When loading `/counties`
   - Then all 3 appear with correct `name`, `lookback_days`,
     `min_lien_amount`, and their sources' `kind`/`url`/`extract_prompt`

2. **`max_steps` override is visible**
   - Given Douglas's `contractor_lien` source has `max_steps: 80` and other
     sources have no explicit `max_steps`
   - When loading `/counties`
   - Then Douglas's `contractor_lien` shows `80` and other sources show the
     default (`40`), clearly distinguishing an explicit override from the
     default

3. **No write path exists**
   - Given the page as implemented
   - When inspecting the page and its API routes
   - Then there is no form, button, or route capable of modifying any county
     YAML file

## Metadata
- **Complexity**: Low
- **Labels**: dashboard, counties-page, read-only
- **Required Skills**: React, Tailwind
