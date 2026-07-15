from __future__ import annotations

import json

import yaml

from bfabric_scripts.cli.login.logout import cmd_login_logout


def _write_config(config_file, *, default="PROD", extra_prod=None):
    prod = {"base_url": "https://example.com/bfabric", "auth_method": "oauth", "client_id": "my-app"}
    prod.update(extra_prod or {})
    config_file.write_text(
        yaml.dump(
            {
                "GENERAL": {"default_config": default},
                "PROD": prod,
                "TEST": {"base_url": "https://test.example.com/bfabric", "login": "user", "password": "x" * 32},
            }
        )
    )


def _environments(config_file):
    data = yaml.safe_load(config_file.read_text())
    return {k for k in data if k != "GENERAL"}


class TestCmdLoginLogout:
    def test_removes_oauth_env_and_clears_cache(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        cache_path = tmp_path / "tok.json"
        cache_path.write_text(json.dumps({"access_token": "tok"}))
        mocker.patch("bfabric_scripts.cli.login.logout.compute_token_cache_path", return_value=cache_path)

        cmd_login_logout("PROD", config_file=config_file, no_confirm=True)

        output = capsys.readouterr().out
        assert "Removed" in output
        assert not cache_path.exists()
        # The environment is gone and, since it was the default, the default is cleared.
        assert _environments(config_file) == {"TEST"}
        data = yaml.safe_load(config_file.read_text())
        assert data.get("GENERAL", {}).get("default_config") is None

    def test_removing_default_env_points_to_auth_default(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login.logout.compute_token_cache_path", return_value=tmp_path / "tok.json")

        cmd_login_logout("PROD", config_file=config_file, no_confirm=True)

        output = capsys.readouterr().out
        # Removing the default while TEST remains must tell the user no default is set and how to fix it.
        assert "auth default" in output
        data = yaml.safe_load(config_file.read_text())
        assert data.get("GENERAL", {}).get("default_config") is None

    def test_removes_non_oauth_env_without_touching_cache(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        clear = mocker.patch("bfabric_scripts.cli.login.logout.TokenCache")

        cmd_login_logout("TEST", config_file=config_file, no_confirm=True)

        assert _environments(config_file) == {"PROD"}
        # A password environment has no OAuth token cache to clear.
        clear.assert_not_called()

    def test_confirmation_declined_keeps_env(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login.logout.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.logout.confirm", return_value=False)

        cmd_login_logout("PROD", config_file=config_file)

        output = capsys.readouterr().out
        assert "No changes made" in output
        assert _environments(config_file) == {"PROD", "TEST"}

    def test_interactive_picker_selects_env(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login.logout.is_interactive", return_value=True)
        pick = mocker.patch("bfabric_scripts.cli.login.logout.select_choice", return_value="TEST")
        mocker.patch("bfabric_scripts.cli.login.logout.confirm", return_value=True)

        cmd_login_logout(config_file=config_file)

        pick.assert_called_once()
        # The picker preselects the current default environment.
        assert pick.call_args.kwargs["default"] == "PROD"
        assert _environments(config_file) == {"PROD"}

    def test_interactive_picker_cancel_keeps_all(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login.logout.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.logout.select_choice", return_value=None)

        cmd_login_logout(config_file=config_file)

        assert _environments(config_file) == {"PROD", "TEST"}

    def test_non_interactive_without_env_aborts(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login.logout.is_interactive", return_value=False)

        cmd_login_logout(config_file=config_file)

        err = capsys.readouterr().err
        assert "--config-env" in err
        assert _environments(config_file) == {"PROD", "TEST"}

    def test_non_interactive_without_no_confirm_refuses(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login.logout.is_interactive", return_value=False)

        cmd_login_logout("PROD", config_file=config_file)

        err = capsys.readouterr().err
        assert "confirm" in err.lower()
        assert _environments(config_file) == {"PROD", "TEST"}

    def test_unknown_env(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        cmd_login_logout("NOPE", config_file=config_file, no_confirm=True)
        output = capsys.readouterr().out
        assert "not found" in output
        assert _environments(config_file) == {"PROD", "TEST"}

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_login_logout("PROD", config_file=config_file, no_confirm=True)
        output = capsys.readouterr().out
        assert "not found" in output
