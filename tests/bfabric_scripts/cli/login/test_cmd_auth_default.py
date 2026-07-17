from __future__ import annotations

import yaml

from bfabric_scripts.cli.login.manage import cmd_auth_default


def _write_config(config_file, default="PROD"):
    general = {"default_config": default} if default is not None else {}
    config_file.write_text(
        yaml.dump(
            {
                "GENERAL": general,
                "PROD": {"base_url": "https://prod.example.com", "auth_method": "oauth"},
                "TEST": {"base_url": "https://test.example.com", "auth_method": "pat", "pat": "tok123"},
            }
        )
    )


class TestSetNonInteractive:
    def test_positional_value_sets_default(self, tmp_path):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        cmd_auth_default("TEST", config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "TEST"

    def test_unknown_env_errors_and_leaves_file_unchanged(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        before = config_file.read_text()
        cmd_auth_default("NOPE", config_file=config_file)
        output = capsys.readouterr().out
        assert "NOPE" in output
        assert config_file.read_text() == before

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_auth_default("PROD", config_file=config_file)
        assert "not found" in capsys.readouterr().out


class TestInteractivePicker:
    def test_selects_default_via_picker(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        # The picker runs only when no value is passed; it returns the chosen environment.
        mocker.patch("bfabric_scripts.cli.login.manage.is_interactive", return_value=True)
        picker = mocker.patch("bfabric_scripts.cli.login.manage.select_choice", return_value="TEST")
        cmd_auth_default(config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "TEST"
        # The current default is pre-selected in the picker.
        assert picker.call_args.kwargs["default"] == "PROD"

    def test_cancelled_picker_leaves_file_unchanged(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        before = config_file.read_text()
        mocker.patch("bfabric_scripts.cli.login.manage.select_choice", return_value=None)
        mocker.patch("bfabric_scripts.cli.login.manage.is_interactive", return_value=True)
        cmd_auth_default(config_file=config_file)
        assert "No changes made" in capsys.readouterr().out
        assert config_file.read_text() == before


class TestNonInteractiveListing:
    def test_lists_environments_when_no_tty_and_no_value(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        before = config_file.read_text()
        mocker.patch("bfabric_scripts.cli.login.manage.is_interactive", return_value=False)
        cmd_auth_default(config_file=config_file)
        output = capsys.readouterr().out
        assert "PROD" in output
        assert "TEST" in output
        # The current default is still marked prominently.
        assert "→ PROD" in output
        # Each row shows the host and auth method so the environments are distinguishable.
        assert "prod.example.com" in output
        assert "oauth" in output
        assert "test.example.com" in output
        assert "pat" in output
        assert config_file.read_text() == before

    def test_empty_config_reports_no_environments(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({"GENERAL": {}}))
        cmd_auth_default(config_file=config_file)
        assert "No environments configured" in capsys.readouterr().out
