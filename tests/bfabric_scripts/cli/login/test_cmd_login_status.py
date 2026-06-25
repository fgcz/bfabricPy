from __future__ import annotations

import pytest
import yaml

from bfabric_scripts.cli.login.status import cmd_login_status


@pytest.fixture(autouse=True)
def _clear_config_env(monkeypatch):
    monkeypatch.delenv("BFABRICPY_CONFIG_ENV", raising=False)


class TestCmdLoginStatus:
    def test_shows_password_auth(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "login": "testuser",
                        "password": "x" * 32,
                    },
                }
            )
        )
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "PROD" in output
        assert "password" in output

    def test_shows_oauth_auth(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "my-app",
                    },
                }
            )
        )
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "oauth" in output
        assert "my-app" in output

    @staticmethod
    def _oauth_config(tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "my-app",
                    },
                }
            )
        )
        return config_file

    def test_shows_oauth_login_when_token_cached(self, tmp_path, capsys, mocker):
        config_file = self._oauth_config(tmp_path)
        mocker.patch("bfabric_scripts.cli.login.status.TokenCache").return_value.load.return_value = {
            "access_token": "x"
        }
        mock_connect = mocker.patch("bfabric_scripts.cli.login.status.Bfabric.connect")
        mock_connect.return_value.current_login = "jdoe"

        cmd_login_status(config_file=config_file)

        output = capsys.readouterr().out
        assert "jdoe" in output
        mock_connect.assert_called_once()

    def test_oauth_login_resolution_failure_is_reported(self, tmp_path, capsys, mocker):
        config_file = self._oauth_config(tmp_path)
        mocker.patch("bfabric_scripts.cli.login.status.TokenCache").return_value.load.return_value = {
            "access_token": "x"
        }
        mocker.patch("bfabric_scripts.cli.login.status.Bfabric.connect", side_effect=RuntimeError("token expired"))

        cmd_login_status(config_file=config_file)

        output = capsys.readouterr().out
        assert "could not resolve" in output
        assert "token expired" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "not found" in output
