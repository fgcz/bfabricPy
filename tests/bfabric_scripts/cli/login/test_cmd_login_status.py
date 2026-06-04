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
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "login": "testuser",
                    "password": "x" * 32,
                },
            })
        )
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "PROD" in output
        assert "password" in output

    def test_shows_oauth_auth(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "oauth",
                    "client_id": "my-app",
                },
            })
        )
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "oauth" in output
        assert "my-app" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "not found" in output
