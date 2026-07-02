---
status: completed
created: 2026-07-01
started: 2026-07-02
completed: 2026-07-02
---
# Task: Machine-Readable Summary Output Contract

## Description
Make `run.py`'s end-of-run summary machine-parseable so that an invoking Claude Code skill/agent (which does have access to the `PushNotification` tool) can read it and send a notification. `run.py` itself, as a plain subprocess, cannot call Claude Code tools directly.

## Background
The design originally assumed `run.py` would "send the push notification" itself; that's not possible for a bare Python script run via `subprocess`/`uv run` outside the Claude Code tool layer. The corrected design has `run.py` print a final structured line that the invoking skill parses and acts on.

## Reference Documentation
**Required:**
- Design: .ralph/specs/lien-prospecting/design.md (see "Driver Script (run.py)" step 8, and "Skill & Scheduling")

**Note:** Read the design document before beginning implementation. This task modifies the `main()`/`__main__` block built in Task 5.

## Technical Requirements
1. After `main()`'s per-county loop completes, build a summary payload: `{"counties": {<name>: {"new": N, "failed_sources": [...]}}, "quiet": bool}`, where `quiet` is `true` only if every county has `new == 0` and `failed_sources == []`.
2. Print exactly one line to stdout as the last line of output: `SUMMARY_JSON: <json payload>` (single line, valid JSON after the prefix — no pretty-printing/multi-line JSON, so it's reliably greppable/parseable by a caller reading stdout).
3. This must be the literal last line printed — no further output (e.g. no trailing "Done!" message) after it, so a caller can safely take the last line of stdout and strip the `SUMMARY_JSON: ` prefix.

## Dependencies
- Task 5 (`task-05-run-py-error-handling-summary.code-task.md`)

## Implementation Approach
1. Modify the `if __name__ == "__main__":` block in `scripts/lien_prospecting/run.py` to build and print the `SUMMARY_JSON:` line as its final action, after any other progress output.
2. Add a test that runs `main()` with mocked county results and asserts the last line of captured stdout matches the expected format.

## Acceptance Criteria

1. **Summary line is machine-parseable and last**
   - Given a completed run (via the script's `__main__` entry point, captured stdout)
   - When the output is split into lines
   - Then the last line matches `^SUMMARY_JSON: \{.*\}$`, and everything after the `SUMMARY_JSON: ` prefix parses as valid JSON matching `{"counties": {...}, "quiet": bool}`

2. **Silent-run flag is correctly set**
   - Given a run where every county has `new: 0` and `failed_sources: []`
   - When the summary payload is built
   - Then `quiet` is `true`

3. **Non-quiet flag when there's anything to report**
   - Given a run where at least one county has `new > 0` OR at least one `failed_sources` entry anywhere
   - When the summary payload is built
   - Then `quiet` is `false`

## Metadata
- **Complexity**: Low
- **Labels**: python, integration, lien-prospecting, notifications
- **Required Skills**: Python, JSON
