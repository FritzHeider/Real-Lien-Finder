---
status: completed
created: 2026-07-01
started: 2026-07-02
completed: 2026-07-02
---
# Task: Palm Beach FL + Douglas CO Configs

## Description
Add the remaining two starting-county configs, using the exact schema established in Task 1.

## Background
Part of the lien-prospecting feature. Three counties were chosen and verified during design: Maricopa AZ (task 1), Palm Beach FL, and Douglas CO — all affluent submarkets with currently-active public lien portals.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "Scope" and "County Config Schema" sections)

**Note:** Read the design document before beginning implementation. Read the completed `scripts/lien_prospecting/counties/maricopa_az.yaml` from Task 1 as the structural template.

## Technical Requirements
1. Create `scripts/lien_prospecting/counties/palm_beach_fl.yaml`:
   - `name`: "Palm Beach County, FL"
   - `sources`: `kind: tax_lien` at `https://taxdeed.mypalmbeachclerk.com`; `kind: contractor_lien` pointing at the Palm Beach County Clerk & Comptroller Official Records search — if the exact search URL isn't stable/known, use `https://www.mypalmbeachclerk.com` as the starting URL and have the `extract_prompt` explicitly instruct the agent to navigate to the Official Records / recorded documents search from there.
   - Same `lookback_days`, `min_lien_amount`, `dedup_key` structure as Task 1.
2. Create `scripts/lien_prospecting/counties/douglas_co.yaml`:
   - `name`: "Douglas County, CO"
   - `sources`: `kind: tax_lien` at `https://www.zeusauction.com` (agent should be instructed in the prompt to select/search for Douglas County, Colorado within the site if it's a multi-county platform); `kind: contractor_lien` at `https://apps.douglas.co.us/LandmarkWeb/`.
3. Both files must use the identical field structure and key names as `maricopa_az.yaml` (schema consistency is required for `run.py` in later tasks to treat all counties uniformly).

## Dependencies
- Task 1 (`task-01-county-config-schema.code-task.md`) — establishes the schema this task follows.

## Implementation Approach
1. Copy the structure of `maricopa_az.yaml` for each new file.
2. Fill in county-specific `name`, `sources[].url`, and `sources[].extract_prompt` (each prompt should request the same field set as Maricopa's, adjusted only for source-specific identifiers if the site doesn't use "parcel_number"/"document_number" terminology — keep `dedup_key` referencing whichever field names each `extract_prompt` actually asks for).
3. Validate both parse with `yaml.safe_load`.

## Acceptance Criteria

1. **Both configs parse and match the established schema**
   - Given `palm_beach_fl.yaml` and `douglas_co.yaml`
   - When each is loaded with `yaml.safe_load`
   - Then both contain `name`, `lookback_days`, `min_lien_amount`, `sources`, `dedup_key`, and `sources` is a non-empty list of `{kind, url, extract_prompt}` objects

2. **dedup_key fields match what each extract_prompt actually requests**
   - Given each county's `sources[].extract_prompt` text
   - When comparing against that county's `dedup_key` list
   - Then every field name in `dedup_key` appears as a requested field in at least one `extract_prompt`

## Metadata
- **Complexity**: Low
- **Labels**: config, yaml, lien-prospecting
- **Required Skills**: YAML
