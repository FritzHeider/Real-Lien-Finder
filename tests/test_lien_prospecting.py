import pytest

from scripts.lien_prospecting import run


COUNTIES_DIR = run.PROJECT_ROOT / "scripts" / "lien_prospecting" / "counties"


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
