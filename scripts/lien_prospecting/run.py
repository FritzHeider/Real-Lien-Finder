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


if __name__ == "__main__":
    pass
