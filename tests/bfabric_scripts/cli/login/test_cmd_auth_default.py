from __future__ import annotations

import pytest
import yaml

from bfabric_scripts.cli.login.default_config import cmd_auth_default_set, cmd_auth_default_show


@pytest.fixture(autouse=True)
def _clear_config_env(monkeypatch):
    monkeypatch.delenv("BFABRICPY_CONFIG_ENV", raising=False)


def _write_config(config_file, default="PROD"):
    general = {"default_config": default} if default is not None else {}
    config_file.write_text(
        yaml.dump(
            {
                "GENERAL": general,
                "PROD": {"base_url": "https://prod.example.com"},
                "TEST": {"base_url": "https://test.example.com"},
            }
        )
    )


class TestCmdAuthDefaultShow:
    def test_lists_environments_and_marks_default(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        cmd_auth_default_show(config_file=config_file)
        output = capsys.readouterr().out
        assert "PROD" in output
        assert "TEST" in output
        assert "(default)" in output
        # The default env is marked prominently with an arrow.
        assert "→ PROD" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_auth_default_show(config_file=config_file)
        assert "not found" in capsys.readouterr().out


class TestCmdAuthDefaultSet:
    def test_sets_default_non_interactively(self, tmp_path):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        cmd_auth_default_set("TEST", config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "TEST"

    def test_prompts_when_env_omitted(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        # The picker shows a numbered menu and asks for a number; env names are sorted
        # (PROD=1, TEST=2), so choosing "2" selects TEST.
        mocker.patch("bfabric_scripts.cli.login.default_config.Prompt.ask", return_value="2")
        cmd_auth_default_set(config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "TEST"
        # The menu is printed with each environment on its own numbered line.
        menu = capsys.readouterr().out
        assert "1. PROD" in menu
        assert "2. TEST" in menu

    def test_unknown_env_errors_and_leaves_file_unchanged(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        before = config_file.read_text()
        cmd_auth_default_set("NOPE", config_file=config_file)
        output = capsys.readouterr().out
        assert "NOPE" in output
        assert config_file.read_text() == before

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_auth_default_set("PROD", config_file=config_file)
        assert "not found" in capsys.readouterr().out
