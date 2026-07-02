---
status: completed
created: 2026-07-01
started: 2026-07-01
completed: 2026-07-02
---
# Task: County Config Schema + Maricopa AZ Config

## Description
Define the YAML schema for a per-county lien-source config and create the first real config file (Maricopa County, AZ). This schema is what makes the lien-prospecting technique "generic" — adding a new county later means adding a YAML file, not writing code.

## Background
This is the first task of the lien-prospecting feature: a daily-automated watch for new tax and contractor liens across a growing list of counties, using the Web-Use browsing agent (a separate sibling project, `src/cli.py`) to read each county's public portal.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "County Config Schema" section)

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. Create the directory `scripts/lien_prospecting/counties/`.
2. Create `scripts/lien_prospecting/counties/maricopa_az.yaml` matching the schema in the design doc exactly:
   - `name`: "Maricopa County, AZ"
   - `lookback_days`: 7
   - `min_lien_amount`: null
   - `sources`: a list of `{kind, url, extract_prompt}` objects. `extract_prompt` must contain the literal substring `{lookback_days}` (templated later by run.py) and must instruct the agent to return ONLY a JSON array with named fields, no prose.
   - `dedup_key`: `["parcel_number", "document_number"]`
3. Two `sources` entries required:
   - `kind: tax_lien`, `url: "https://maricopa.arizonataxsale.com"`
   - `kind: contractor_lien`, `url: "https://recorder.maricopa.gov/recording/document-search.html"`
4. No Python code in this task — YAML only. Later tasks consume this file.

## Dependencies
None — this is the first task.

## Implementation Approach
1. Create `scripts/lien_prospecting/counties/`.
2. Write `maricopa_az.yaml` per the schema above, copying the exact field structure from the design doc's example.
3. Validate it parses: `uv run python -c "import yaml; print(yaml.safe_load(open('scripts/lien_prospecting/counties/maricopa_az.yaml')))"`.

## Acceptance Criteria

1. **Config parses as valid YAML**
   - Given the file `scripts/lien_prospecting/counties/maricopa_az.yaml` exists
   - When it is loaded with `yaml.safe_load`
   - Then it parses without error and contains `name`, `lookback_days`, `min_lien_amount`, `sources`, `dedup_key` keys

2. **Both sources present and well-formed**
   - Given the parsed config
   - When inspecting `sources`
   - Then there are exactly two entries with `kind` values `tax_lien` and `contractor_lien`, each with a non-empty `url` and an `extract_prompt` containing the literal substring `{lookback_days}`

## Metadata
- **Complexity**: Low
- **Labels**: config, yaml, lien-prospecting
- **Required Skills**: YAML
