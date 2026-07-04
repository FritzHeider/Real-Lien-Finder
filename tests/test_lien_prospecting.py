import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.lien_prospecting import run


COUNTIES_DIR = run.PROJECT_ROOT / "scripts" / "lien_prospecting" / "counties"

SOURCE = {
    "kind": "tax_lien",
    "url": "https://example-county.gov/liens",
    "extract_prompt": (
        "Find tax liens filed in the last {lookback_days} days. "
        "Return ONLY a JSON array of objects, no prose."
    ),
}


class TestResolveWebUseDir:
    def test_missing_checkout_raises_clear_error(self, tmp_path, monkeypatch):
        empty_dir = tmp_path / "not-web-use"
        empty_dir.mkdir()
        monkeypatch.setenv("WEB_USE_DIR", str(empty_dir))

        with pytest.raises(RuntimeError, match="Web-Use"):
            run.resolve_web_use_dir()

    def test_valid_checkout_returns_path(self, tmp_path, monkeypatch):
        web_use_dir = tmp_path / "Web-Use"
        (web_use_dir / "src").mkdir(parents=True)
        (web_use_dir / "src" / "cli.py").write_text("# stub cli\n")
        monkeypatch.setenv("WEB_USE_DIR", str(web_use_dir))

        result = run.resolve_web_use_dir()

        assert result == web_use_dir.resolve()

    def test_defaults_to_sibling_web_use_dir_when_env_unset(self, tmp_path, monkeypatch):
        fake_project_root = tmp_path / "lien-prospecting"
        fake_project_root.mkdir()
        fake_web_use_dir = tmp_path / "Web-Use"
        (fake_web_use_dir / "src").mkdir(parents=True)
        (fake_web_use_dir / "src" / "cli.py").write_text("# stub cli\n")

        monkeypatch.delenv("WEB_USE_DIR", raising=False)
        monkeypatch.setattr(run, "PROJECT_ROOT", fake_project_root)

        result = run.resolve_web_use_dir()

        assert result == (fake_project_root / ".." / "Web-Use").resolve()
        assert result == fake_web_use_dir.resolve()


class TestLoadCounties:
    def test_loads_every_yaml_and_tags_source(self):
        counties = run.load_counties(COUNTIES_DIR)

        assert len(counties) == 3
        slugs = {county["_slug"] for county in counties}
        assert slugs == {"maricopa_az", "palm_beach_fl", "douglas_co"}
        for county in counties:
            assert county["_source_file"].endswith(".yaml")
            assert "sources" in county


class TestBuildPrompt:
    def test_formats_lookback_days_into_extract_prompt(self):
        source = {"extract_prompt": "Find liens filed in the last {lookback_days} days."}

        prompt = run.build_prompt(source, 7)

        assert prompt == "Find liens filed in the last 7 days."

    def test_ignores_unrelated_braces_not_present(self):
        source = {"extract_prompt": "Look back {lookback_days} days for parcel data."}

        prompt = run.build_prompt(source, 14)

        assert "14" in prompt
        assert "{lookback_days}" not in prompt


class TestRunExtraction:
    def test_valid_json_parses_cleanly(self):
        mock_result = MagicMock(
            returncode=0,
            stdout=(
                "[*] Starting Web-Use Agent...\n"
                "[+] Final Agent Response:\n"
                '[{"parcel_number": "123", "owner_name": "Jane Doe", "lien_amount": 500}]\n'
            ),
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert failure is None
        assert rows == [
            {"parcel_number": "123", "owner_name": "Jane Doe", "lien_amount": 500}
        ]

    def test_prose_wrapped_json_recovered_via_regex_fallback(self):
        mock_result = MagicMock(
            returncode=0,
            stdout=(
                "[+] Final Agent Response:\n"
                "Here are the results:\n"
                '[{"parcel_number": "456", "owner_name": "John Smith", "lien_amount": 1200}]\n'
                "Let me know if you need more.\n"
            ),
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert failure is None
        assert rows == [
            {"parcel_number": "456", "owner_name": "John Smith", "lien_amount": 1200}
        ]

    def test_missing_marker_does_not_fabricate_rows_from_stray_bracket_text(self):
        # No "[+] Final Agent Response:" marker anywhere. A stray bracketed
        # array happens to sit at the byte offset the old buggy slice
        # (stdout[-1 + len(marker):]) would land on, so this must NOT be
        # parsed as a real result.
        mock_result = MagicMock(
            returncode=0,
            stdout="x" * 24 + '[{"parcel_number": "FAKE", "lien_amount": 999999}]',
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure is not None

    def test_no_marker_returns_max_steps_exhausted(self):
        mock_result = MagicMock(
            returncode=0,
            stdout="[*] Starting Web-Use Agent...\n[*] Step 40/40 reached.\n",
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure == "max_steps_exhausted"

    def test_marker_present_but_unparsable_returns_invalid_json(self):
        mock_result = MagicMock(
            returncode=0,
            stdout="[+] Final Agent Response:\nI could not find any lien data.\n",
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure == "invalid_json"

    def test_max_steps_reached_with_marker_present_returns_max_steps_exhausted(self):
        # Web-Use's cli.py prints the marker+last message unconditionally,
        # even when the agent hit its step budget mid-navigation (e.g. stuck
        # clicking stale DOM indices on a multi-step doc-search UI) — so the
        # marker being present doesn't mean the run actually completed.
        mock_result = MagicMock(
            returncode=0,
            stdout=(
                "[Agent] \U0001f6a8 Error: Agent reached max steps (40) without completing.\n\n"
                "[+] Final Agent Response:\n"
                "Navigated to https://example-county.gov/liens\n"
            ),
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure == "max_steps_exhausted"

    def test_browser_abort_with_marker_present_returns_agent_aborted(self):
        # A crashed browser/CDP session (e.g. "no close frame received or
        # sent") makes the agent abort after repeated tool failures; the
        # marker text left behind is a stale action description, not data.
        mock_result = MagicMock(
            returncode=0,
            stdout=(
                "[Agent] \U0001f6a8 Error: Agent aborted after 3 consecutive failures. "
                "Last: Tool 'goto_tool' async failed: no close frame received or sent\n\n"
                "[+] Final Agent Response:\n"
                "Navigated to https://example-county.gov/liens\n"
            ),
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure == "agent_aborted"

    def test_non_zero_exit_code_returns_subprocess_error(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="boom")

        with patch("subprocess.run", return_value=mock_result):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure == "subprocess_error"

    def test_subprocess_timeout_returns_subprocess_error_without_raising(self):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="uv run python src/cli.py", timeout=300),
        ):
            rows, failure = run.run_extraction(
                "Maricopa AZ", SOURCE, 7, Path("/fake/web-use")
            )

        assert rows is None
        assert failure == "subprocess_error"

    def test_invokes_subprocess_with_expected_args(self):
        web_use_dir = Path("/fake/web-use")
        mock_result = MagicMock(
            returncode=0,
            stdout="[+] Final Agent Response:\n[]\n",
            stderr="",
        )

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run.run_extraction("Maricopa AZ", SOURCE, 7, web_use_dir)

        args, kwargs = mock_run.call_args
        command = args[0]
        assert command[:3] == ["uv", "run", "python"]
        assert "src/cli.py" in command
        assert "--headless" in command
        assert "--steps" in command
        assert "40" in command
        assert kwargs["cwd"] == web_use_dir
        assert kwargs["timeout"] == 300
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True


class TestApplyMinLienAmount:
    def test_none_min_amount_returns_rows_unchanged(self):
        rows = [{"lien_amount": 500}, {"lien_amount": "unknown"}]

        result = run.apply_min_lien_amount(rows, None)

        assert result == rows

    def test_filters_below_threshold_and_keeps_non_numeric(self):
        rows = [
            {"lien_amount": 500},
            {"lien_amount": 2000},
            {"lien_amount": "unknown"},
        ]

        result = run.apply_min_lien_amount(rows, 1000)

        assert result == [{"lien_amount": 2000}, {"lien_amount": "unknown"}]

    def test_keeps_row_with_missing_lien_amount_key(self):
        rows = [{"parcel_number": "123"}, {"lien_amount": 5000}]

        result = run.apply_min_lien_amount(rows, 1000)

        assert result == [{"parcel_number": "123"}, {"lien_amount": 5000}]


class TestLoadLedger:
    def test_missing_file_returns_empty_list(self, tmp_path):
        result = run.load_ledger(tmp_path / "does-not-exist.csv")

        assert result == []

    def test_parses_existing_csv_into_row_dicts(self, tmp_path):
        path = tmp_path / "maricopa_az.csv"
        path.write_text(
            "first_seen,source_kind,parcel_number,owner_name\n"
            "2026-07-01,tax_lien,123,Jane Doe\n"
        )

        result = run.load_ledger(path)

        assert result == [
            {
                "first_seen": "2026-07-01",
                "source_kind": "tax_lien",
                "parcel_number": "123",
                "owner_name": "Jane Doe",
            }
        ]


class TestRowKey:
    def test_uses_present_dedup_key_fields(self):
        row = {"parcel_number": "123", "document_number": "", "owner_name": "Jane Doe"}

        result = run.row_key(row, ["parcel_number", "document_number"])

        assert result == "123"

    def test_joins_multiple_present_dedup_key_fields(self):
        row = {"parcel_number": "123", "document_number": "456"}

        result = run.row_key(row, ["parcel_number", "document_number"])

        assert result == "123|456"

    def test_fallback_hash_is_deterministic_for_identical_rows(self):
        row_a = {
            "owner_name": "Jane Doe",
            "property_address": "1 Main St",
            "filing_date": "2026-07-01",
        }
        row_b = dict(row_a)

        key_a = run.row_key(row_a, ["parcel_number", "document_number"])
        key_b = run.row_key(row_b, ["parcel_number", "document_number"])

        assert key_a == key_b
        assert key_a != ""

    def test_fallback_differs_for_different_rows(self):
        row_a = {
            "owner_name": "Jane Doe",
            "property_address": "1 Main St",
            "filing_date": "2026-07-01",
        }
        row_b = {
            "owner_name": "John Smith",
            "property_address": "2 Main St",
            "filing_date": "2026-07-01",
        }

        assert run.row_key(row_a, ["parcel_number"]) != run.row_key(row_b, ["parcel_number"])


class TestDiffNewRows:
    def test_excludes_rows_already_in_ledger(self):
        existing_rows = [{"parcel_number": "123", "owner_name": "Jane Doe"}]
        parsed_rows = [
            {"parcel_number": "123", "owner_name": "Jane Doe"},
            {"parcel_number": "456", "owner_name": "John Smith"},
        ]

        result = run.diff_new_rows(parsed_rows, existing_rows, ["parcel_number"])

        assert result == [{"parcel_number": "456", "owner_name": "John Smith"}]

    def test_no_existing_rows_returns_all_parsed_rows(self):
        parsed_rows = [{"parcel_number": "123", "owner_name": "Jane Doe"}]

        result = run.diff_new_rows(parsed_rows, [], ["parcel_number"])

        assert result == parsed_rows

    def test_dedups_via_fallback_hash_when_dedup_key_fields_absent(self):
        row = {
            "owner_name": "Jane Doe",
            "property_address": "1 Main St",
            "filing_date": "2026-07-01",
        }
        existing_rows = [dict(row)]
        parsed_rows = [dict(row)]

        result = run.diff_new_rows(parsed_rows, existing_rows, ["parcel_number", "document_number"])

        assert result == []


class TestAppendLedger:
    def test_creates_file_with_header_and_rows(self, tmp_path):
        path = tmp_path / "maricopa_az.csv"
        new_rows = [{"parcel_number": "123", "owner_name": "Jane Doe"}]

        run.append_ledger(path, new_rows, "tax_lien", "https://example.com", "2026-07-02")

        result = run.load_ledger(path)
        assert result == [
            {
                "first_seen": "2026-07-02",
                "source_kind": "tax_lien",
                "parcel_number": "123",
                "document_number": "",
                "owner_name": "Jane Doe",
                "property_address": "",
                "lien_amount": "",
                "filing_date": "",
                "source_url": "https://example.com",
            }
        ]

    def test_appends_without_rewriting_header(self, tmp_path):
        path = tmp_path / "maricopa_az.csv"
        run.append_ledger(path, [{"parcel_number": "123"}], "tax_lien", "url", "2026-07-01")

        run.append_ledger(path, [{"parcel_number": "456"}], "tax_lien", "url", "2026-07-02")

        result = run.load_ledger(path)
        assert len(result) == 2
        assert [row["parcel_number"] for row in result] == ["123", "456"]

    def test_missing_lien_amount_does_not_raise(self, tmp_path):
        path = tmp_path / "maricopa_az.csv"
        row_missing_lien_amount = {"parcel_number": "123", "owner_name": "Jane Doe"}

        run.append_ledger(path, [row_missing_lien_amount], "tax_lien", "url", "2026-07-02")

        result = run.load_ledger(path)
        assert result[0]["lien_amount"] == ""
