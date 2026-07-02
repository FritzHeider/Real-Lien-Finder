"""Driver for the lien-prospecting watch.

Loads per-county YAML configs, drives the Web-Use browsing agent
(a sibling project's ``src/cli.py``) to extract lien data per source, and
will (in later tasks) diff results against a per-county ledger.
"""

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


if __name__ == "__main__":
    pass
