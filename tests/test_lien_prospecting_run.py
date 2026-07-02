import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.lien_prospecting import run


def _write_county_yaml(counties_dir: Path, slug: str, name: str) -> None:
    (counties_dir / f"{slug}.yaml").write_text(
        f'name: "{name}"\n'
        "lookback_days: 7\n"
        "min_lien_amount: null\n"
        "sources:\n"
        "  - kind: tax_lien\n"
        '    url: "https://example-county.gov/liens"\n'
        '    extract_prompt: "Find liens. Return ONLY a JSON array, no prose."\n'
        'dedup_key: ["parcel_number"]\n'
    )


def _write_stub_web_use_dir(base: Path) -> Path:
    web_use_dir = base / "Web-Use"
    (web_use_dir / "src").mkdir(parents=True)
    (web_use_dir / "src" / "cli.py").write_text("# stub cli, never actually invoked in tests\n")
    return web_use_dir


class TestRunCounty:
    def test_success_appends_new_rows_and_returns_zero_failures(self, tmp_path):
        county_config = {
            "name": "Test County",
            "lookback_days": 7,
            "min_lien_amount": None,
            "dedup_key": ["parcel_number"],
            "sources": [{"kind": "tax_lien", "url": "https://example.com", "extract_prompt": "x"}],
            "_ledger_path": tmp_path / "test_county.csv",
        }

        with patch.object(
            run,
            "run_extraction",
            return_value=([{"parcel_number": "123", "owner_name": "Jane Doe"}], None),
        ):
            result = run.run_county(county_config, Path("/fake/web-use"))

        assert result == {"new": 1, "failed_sources": []}
        assert len(run.load_ledger(county_config["_ledger_path"])) == 1

    def test_source_failure_is_collected_not_raised(self, tmp_path):
        county_config = {
            "name": "Test County",
            "lookback_days": 7,
            "min_lien_amount": None,
            "dedup_key": ["parcel_number"],
            "sources": [{"kind": "tax_lien", "url": "https://example.com", "extract_prompt": "x"}],
            "_ledger_path": tmp_path / "test_county.csv",
        }

        with patch.object(run, "run_extraction", return_value=(None, "invalid_json")):
            result = run.run_county(county_config, Path("/fake/web-use"))

        assert result == {
            "new": 0,
            "failed_sources": [
                {"source_kind": "tax_lien", "url": "https://example.com", "reason": "invalid_json"}
            ],
        }


class TestMain:
    def test_one_county_failure_does_not_stop_others(self, tmp_path, monkeypatch):
        counties_dir = tmp_path / "counties"
        counties_dir.mkdir()
        _write_county_yaml(counties_dir, "county_one", "County One")
        _write_county_yaml(counties_dir, "county_two", "County Two")
        _write_county_yaml(counties_dir, "county_three", "County Three")

        monkeypatch.setenv("WEB_USE_DIR", str(_write_stub_web_use_dir(tmp_path)))
        monkeypatch.setattr(run, "RUN_LOG_PATH", tmp_path / "run.log")

        def fake_run_extraction(county_name, source, lookback_days, web_use_dir):
            if county_name == "County Two":
                return None, "invalid_json"
            return [{"parcel_number": "123", "owner_name": "Jane Doe"}], None

        with patch.object(run, "run_extraction", side_effect=fake_run_extraction):
            summary = run.main(counties_dir=counties_dir, ledger_dir=tmp_path / "ledger")

        assert summary["County One"] == {"new": 1, "failed_sources": []}
        assert summary["County Three"] == {"new": 1, "failed_sources": []}
        assert summary["County Two"]["new"] == 0
        assert len(summary["County Two"]["failed_sources"]) == 1

    def test_county_flag_scopes_to_one_county(self, tmp_path, monkeypatch):
        counties_dir = tmp_path / "counties"
        counties_dir.mkdir()
        _write_county_yaml(counties_dir, "maricopa_az", "Maricopa County, AZ")
        _write_county_yaml(counties_dir, "palm_beach_fl", "Palm Beach County, FL")
        _write_county_yaml(counties_dir, "douglas_co", "Douglas County, CO")

        monkeypatch.setenv("WEB_USE_DIR", str(_write_stub_web_use_dir(tmp_path)))
        monkeypatch.setattr(run, "RUN_LOG_PATH", tmp_path / "run.log")

        with patch.object(run, "run_extraction", return_value=([], None)):
            summary = run.main(
                counties_dir=counties_dir,
                ledger_dir=tmp_path / "ledger",
                county_filter="maricopa_az",
            )

        assert list(summary.keys()) == ["Maricopa County, AZ"]

    def test_failure_is_logged_with_county_url_and_reason(self, tmp_path, monkeypatch):
        counties_dir = tmp_path / "counties"
        counties_dir.mkdir()
        _write_county_yaml(counties_dir, "county_one", "County One")

        log_path = tmp_path / "run.log"
        monkeypatch.setenv("WEB_USE_DIR", str(_write_stub_web_use_dir(tmp_path)))
        monkeypatch.setattr(run, "RUN_LOG_PATH", log_path)

        with patch.object(run, "run_extraction", return_value=(None, "invalid_json")):
            run.main(counties_dir=counties_dir, ledger_dir=tmp_path / "ledger")

        log_contents = log_path.read_text()
        assert "County One" in log_contents
        assert "https://example-county.gov/liens" in log_contents
        assert "invalid_json" in log_contents

    def test_missing_web_use_dir_raises_immediately(self, tmp_path, monkeypatch):
        counties_dir = tmp_path / "counties"
        counties_dir.mkdir()
        _write_county_yaml(counties_dir, "county_one", "County One")
        monkeypatch.setenv("WEB_USE_DIR", str(tmp_path / "not-web-use"))

        with pytest.raises(RuntimeError, match="Web-Use"):
            run.main(counties_dir=counties_dir, ledger_dir=tmp_path / "ledger")


class TestParseArgs:
    def test_county_flag_maps_to_county_filter(self):
        args = run.parse_args(["--county", "maricopa_az"])

        assert args.county == "maricopa_az"

    def test_county_flag_defaults_to_none(self):
        args = run.parse_args([])

        assert args.county is None


class TestBuildSummaryPayload:
    def test_quiet_true_when_every_county_clean(self):
        payload = run.build_summary_payload(
            {"County One": {"new": 0, "failed_sources": []}}
        )

        assert payload == {"counties": {"County One": {"new": 0, "failed_sources": []}}, "quiet": True}

    def test_quiet_false_when_a_county_has_new_rows(self):
        payload = run.build_summary_payload(
            {"County One": {"new": 3, "failed_sources": []}}
        )

        assert payload["quiet"] is False

    def test_quiet_false_when_any_county_has_a_failure(self):
        payload = run.build_summary_payload(
            {
                "County One": {"new": 0, "failed_sources": []},
                "County Two": {"new": 0, "failed_sources": [{"source_kind": "tax_lien", "url": None, "reason": "invalid_json"}]},
            }
        )

        assert payload["quiet"] is False


class TestMainSubprocessExitCode:
    def test_process_exits_zero_even_when_every_source_fails(self, tmp_path):
        # Isolated copy of the project layout so this never touches the real
        # scripts/lien_prospecting/ledger or run.log, and never needs a real
        # Web-Use checkout / GOOGLE_API_KEY.
        project_root = tmp_path / "project"
        pkg_dir = project_root / "scripts" / "lien_prospecting"
        pkg_dir.mkdir(parents=True)
        pkg_dir.joinpath("run.py").write_text(Path(run.__file__).read_text())

        counties_dir = pkg_dir / "counties"
        counties_dir.mkdir()
        _write_county_yaml(counties_dir, "county_one", "County One")

        web_use_dir = _write_stub_web_use_dir(tmp_path)

        result = subprocess.run(
            [sys.executable, str(pkg_dir / "run.py")],
            cwd=project_root,
            env={**os.environ, "WEB_USE_DIR": str(web_use_dir)},
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0

    def test_last_stdout_line_is_valid_summary_json(self, tmp_path):
        # Same isolated-copy setup as above, but this asserts on the
        # SUMMARY_JSON: contract (task-06 AC#1): it must be the literal last
        # line of stdout and parse as {"counties": {...}, "quiet": bool}.
        project_root = tmp_path / "project"
        pkg_dir = project_root / "scripts" / "lien_prospecting"
        pkg_dir.mkdir(parents=True)
        pkg_dir.joinpath("run.py").write_text(Path(run.__file__).read_text())

        counties_dir = pkg_dir / "counties"
        counties_dir.mkdir()
        _write_county_yaml(counties_dir, "county_one", "County One")

        web_use_dir = _write_stub_web_use_dir(tmp_path)

        result = subprocess.run(
            [sys.executable, str(pkg_dir / "run.py")],
            cwd=project_root,
            env={**os.environ, "WEB_USE_DIR": str(web_use_dir)},
            capture_output=True,
            text=True,
            timeout=60,
        )

        lines = result.stdout.strip("\n").splitlines()
        last_line = lines[-1]

        assert re.match(r"^SUMMARY_JSON: \{.*\}$", last_line)
        payload = json.loads(last_line[len("SUMMARY_JSON: "):])
        assert set(payload.keys()) == {"counties", "quiet"}
        assert isinstance(payload["quiet"], bool)
        assert "County One" in payload["counties"]
