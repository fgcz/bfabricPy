from __future__ import annotations

import json
import time

import pytest
import yaml

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
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

    def test_shows_pat_auth(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "pat",
                        "pat": "short-pat-token",
                    },
                }
            )
        )
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "pat" in output
        # The secret itself must never be printed.
        assert "short-pat-token" not in output

    def test_oauth_reports_missing_token_and_unrecorded_scope(self, tmp_path, capsys, mocker):
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
        # No cache file on disk -> missing token, no scope to report.
        mocker.patch("bfabric_scripts.cli.login.status.compute_token_cache_path", return_value=tmp_path / "absent.json")
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "missing" in output
        assert "(not recorded)" in output

    def test_oauth_shows_matched_scope_and_expiry_when_cached(self, tmp_path, capsys, mocker):
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
        cache_path = tmp_path / "tok.json"
        cache_path.write_text(
            json.dumps({"access_token": "x", "scope": f"{DEFAULT_OAUTH_SCOPE} tus", "expires_at": time.time() + 9000})
        )
        mocker.patch("bfabric_scripts.cli.login.status.compute_token_cache_path", return_value=cache_path)
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        # The granted scope matches the read-write-upload preset and the token is still valid.
        assert "read-write-upload" in output
        assert "expires in" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_login_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "not found" in output
