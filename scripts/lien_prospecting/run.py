"""Driver for the lien-prospecting watch.

Loads per-county YAML configs, drives the Web-Use browsing agent
(a sibling project's ``src/cli.py``) to extract lien data per source, and
will (in later tasks) diff results against a per-county ledger.
"""

import csv
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def resolve_web_use_dir() -> Path:
    """Resolve the Web-Use checkout path from WEB_USE_DIR, defaulting to ../Web-Use.

    Raises loudly at startup if the resolved path doesn't contain src/cli.py,
    so a missing/misconfigured checkout fails clearly instead of producing a
    confusing subprocess_error for every source later on.
    """
    raw_path = os.environ.get("WEB_USE_DIR", str(PROJECT_ROOT / ".." / "Web-Use"))
    web_use_dir = Path(raw_path).resolve()
    cli_path = web_use_dir / "src" / "cli.py"

    if not cli_path.is_file():
        raise RuntimeError(
            f"Web-Use checkout not found at {web_use_dir} (missing {cli_path}). "
            "Set the WEB_USE_DIR environment variable to a valid Web-Use "
            "checkout, or ensure a sibling '../Web-Use' directory exists with "
            "src/cli.py."
        )

    return web_use_dir


def load_counties(counties_dir: Path) -> list[dict]:
    """Load and parse every county YAML config in counties_dir.

    Each returned dict is tagged with its source filename (_source_file) and
    slug (_slug) for use in later stages (extraction, ledger diffing).
    """
    counties = []

    for path in sorted(counties_dir.glob("*.yaml")):
        with path.open() as f:
            config = yaml.safe_load(f)
        config["_source_file"] = path.name
        config["_slug"] = path.stem
        counties.append(config)

    return counties


def build_prompt(source: dict, lookback_days: int) -> str:
    """Format source['extract_prompt'], substituting {lookback_days}."""
    return source["extract_prompt"].format(lookback_days=lookback_days)


FINAL_RESPONSE_MARKER = "[+] Final Agent Response:"


def run_extraction(
    county_name: str, source: dict, lookback_days: int, web_use_dir: Path
) -> tuple[list[dict] | None, str | None]:
    """Drive Web-Use's src/cli.py for one source and parse its final answer.

    Returns (rows, None) on success, or (None, failure_reason) otherwise.
    """
    prompt = build_prompt(source, lookback_days)
    url = source.get("url")
    if url and url not in prompt:
        prompt = f"Start at {url}. {prompt}"

    try:
        result = subprocess.run(
            ["uv", "run", "python", "src/cli.py", "--query", prompt, "--headless", "--steps", "40"],
            cwd=web_use_dir,
            timeout=300,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return None, "subprocess_error"

    if result.returncode != 0:
        return None, "subprocess_error"

    marker_index = result.stdout.find(FINAL_RESPONSE_MARKER)
    if marker_index == -1:
        return None, "max_steps_exhausted"
    text = result.stdout[marker_index + len(FINAL_RESPONSE_MARKER):].strip()

    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0)), None
        except json.JSONDecodeError:
            pass

    return None, "invalid_json"


def apply_min_lien_amount(rows: list[dict], min_amount: float | None) -> list[dict]:
    """Keep rows whose lien_amount >= min_amount; keep non-numeric/missing as-is."""
    if min_amount is None:
        return rows

    kept = []
    for row in rows:
        try:
            amount = float(row["lien_amount"])
        except (KeyError, TypeError, ValueError):
            kept.append(row)
            continue
        if amount >= min_amount:
            kept.append(row)

    return kept


def row_key(row: dict, dedup_key: list[str]) -> str:
    """Build a dedup key from the present/non-empty dedup_key fields.

    Falls back to a sha1 hash of (owner_name, property_address, filing_date)
    when none of the dedup_key fields are present/non-empty, so a row is
    never silently dropped or falsely re-flagged as new every run.
    """
    present = [str(row[k]) for k in dedup_key if row.get(k)]
    if present:
        return "|".join(present)

    fallback = "|".join(
        str(row.get(field, "")) for field in ("owner_name", "property_address", "filing_date")
    )
    return hashlib.sha1(fallback.encode()).hexdigest()


def load_ledger(path: Path) -> list[dict]:
    """Read a county ledger CSV into a list of row dicts; [] if it doesn't exist."""
    if not path.exists():
        return []

    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def diff_new_rows(
    parsed_rows: list[dict], existing_rows: list[dict], dedup_key: list[str]
) -> list[dict]:
    """Return the parsed_rows whose row_key isn't already in existing_rows."""
    existing_keys = {row_key(row, dedup_key) for row in existing_rows}
    return [row for row in parsed_rows if row_key(row, dedup_key) not in existing_keys]


LEDGER_FIELDS = [
    "first_seen",
    "source_kind",
    "parcel_number",
    "document_number",
    "owner_name",
    "property_address",
    "lien_amount",
    "filing_date",
    "source_url",
]


def append_ledger(
    path: Path, new_rows: list[dict], source_kind: str, source_url: str, run_date: str
) -> None:
    """Append new_rows to the ledger CSV at path, creating it with the header if missing."""
    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if write_header:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(
                {field: row.get(field, "") for field in LEDGER_FIELDS}
                | {"first_seen": run_date, "source_kind": source_kind, "source_url": source_url}
            )


if __name__ == "__main__":
    pass
