---
status: completed
created: 2026-07-01
started: 2026-07-02
completed: 2026-07-02
---
# Task: lien-prospecting SKILL.md

## Description
Write the Claude Code skill that documents this feature: ad-hoc usage, how to add a county, where results live, and — critically — the required follow-up step of turning `run.py`'s printed summary into a push notification (since `run.py` can't do that itself; see Task 6).

## Background
This is a standalone project (a sibling of Web-Use, not a subfolder of it). Follow the same pattern as Web-Use's own `.claude/skills/web-use-agent/SKILL.md` (project-scoped, technique/reference type skill, verified with a real invocation rather than just written and assumed to work) — read it from the Web-Use checkout for style/tone precedent.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "External Dependency: Web-Use" and "Skill & Scheduling")

**Additional References:**
- `<WEB_USE_DIR>/.claude/skills/web-use-agent/SKILL.md` (e.g. `../Web-Use/.claude/skills/web-use-agent/SKILL.md`) — precedent for skill style/tone and the "verify with a real run" bar
- `scripts/lien_prospecting/counties/*.yaml` (Tasks 1-2) — for accurately documenting the config schema

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. Create `.claude/skills/lien-prospecting/SKILL.md` with YAML frontmatter:
   - `name: lien-prospecting`
   - `description`: starts with "Use when asked to run lien prospecting, check for new tax/contractor liens, or add a county to the lien-watch list." — describe triggering conditions only, not the internal workflow (per this convention).
2. Body must document:
   - What this does in 2-3 sentences (daily-ledger lien watch across configured counties, dogfooding the Web-Use agent for page-reading).
   - Prerequisite: a Web-Use checkout must be available; defaults to `../Web-Use` (sibling directory), overridable via the `WEB_USE_DIR` environment variable.
   - Ad-hoc usage: `uv run python scripts/lien_prospecting/run.py` (all counties) and `uv run python scripts/lien_prospecting/run.py --county <slug>` (one county).
   - How to add a county: drop a new YAML into `scripts/lien_prospecting/counties/` matching the schema (name, lookback_days, min_lien_amount, sources, dedup_key) — no code change required.
   - Where results live: `scripts/lien_prospecting/ledger/<slug>.csv`, and `scripts/lien_prospecting/run.log` for failure details.
   - **Required follow-up step**: after running `run.py`, read the last line of its output (`SUMMARY_JSON: {...}`), parse it, and call `PushNotification` with a human-readable summary (total new liens, per-county breakdown, any failed sources) — unless `quiet: true`, in which case skip the notification.

## Dependencies
- Task 2 (`task-02-remaining-county-configs.code-task.md`) — accurate config-schema documentation needs the real configs to exist.
- Task 6 (`task-06-summary-output-contract.code-task.md`) — the `SUMMARY_JSON:` contract this skill documents must be finalized first.

## Implementation Approach
1. Write `.claude/skills/lien-prospecting/SKILL.md` following the structure and concision of `.claude/skills/web-use-agent/SKILL.md`.
2. Verify by actually running the documented ad-hoc command for at least one county (`--county maricopa_az`) and confirming it completes without a Python traceback (site/network failures are expected and fine — they should show up as `failed_sources`, not a crash).

## Acceptance Criteria

1. **Skill file exists with valid frontmatter**
   - Given `.claude/skills/lien-prospecting/SKILL.md`
   - When its YAML frontmatter is parsed
   - Then it has `name: lien-prospecting` and a `description` field starting with "Use when"

2. **Documented ad-hoc command actually works**
   - Given the exact command documented in SKILL.md for running one county
   - When it is run against `--county maricopa_az`
   - Then the process exits 0 and prints a `SUMMARY_JSON:` line as its last line (network/site failures inside that county's sources are acceptable and expected to appear in `failed_sources`, not as a crash)

3. **Add-a-county instructions are accurate**
   - Given the SKILL.md's documented config schema
   - When compared field-by-field against `scripts/lien_prospecting/counties/maricopa_az.yaml`
   - Then every documented field name matches the actual schema exactly

## Metadata
- **Complexity**: Low
- **Labels**: documentation, skill, lien-prospecting
- **Required Skills**: Markdown, YAML frontmatter
