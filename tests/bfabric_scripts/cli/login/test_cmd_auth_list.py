from __future__ import annotations

import base64
import json
import time

import yaml

from bfabric_scripts.cli.login.manage import cmd_auth_list


class TestCmdAuthList:
    def test_lists_environments_and_marks_default(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "TEST"},
                    "PROD": {"base_url": "https://prod.example.com", "auth_method": "oauth"},
                    "TEST": {"base_url": "https://test.example.com", "auth_method": "pat", "pat": "tok"},
                }
            )
        )
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "PROD" in output
        assert "TEST" in output
        # The default is flagged and each row carries the host + auth method.
        assert "(default)" in output
        assert "prod.example.com" in output
        assert "oauth" in output
        assert "pat" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "not found" in output

    def test_no_environments(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({"GENERAL": {}}))
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "No environments configured" in output


class TestListDisplay:
    """The listing carries what disambiguates several logins on one instance."""

    def _write(self, config_file):
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "prod-ro"},
                    "prod-ro": {
                        "base_url": "https://prod.example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "CLI",
                        "scope": "api:read",
                    },
                    "prod-rw": {
                        "base_url": "https://prod.example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "CLI",
                        "scope": "api:write",
                    },
                    "other": {"base_url": "https://other.example.com/bfabric", "auth_method": "pat", "pat": "t"},
                }
            )
        )

    def test_groups_by_host(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        self._write(config_file)
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=tmp_path / "absent.json")
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        # Each host is a heading, printed once, above its environments.
        assert output.count("prod.example.com") == 1
        assert output.index("prod.example.com") < output.index("prod-ro")
        assert "other.example.com" in output

    def test_shows_the_scope_and_expiry_of_each_cached_token(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        self._write(config_file)
        cache_path = tmp_path / "tok.json"
        cache_path.write_text(json.dumps({"access_token": "t", "expires_at": time.time() + 3600}))
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=cache_path)
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "api:read" in output
        assert "expires in" in output

    def test_marks_a_logged_out_environment(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        self._write(config_file)
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=tmp_path / "absent.json")
        cmd_auth_list(config_file=config_file)
        assert "logged out" in capsys.readouterr().out

    def test_annotates_why_an_environment_is_active(self, tmp_path, capsys, mocker, monkeypatch):
        config_file = tmp_path / "config.yml"
        self._write(config_file)
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=tmp_path / "absent.json")
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "prod-rw")
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        # The env var outranks the configured default, which is otherwise invisible.
        assert "active via BFABRICPY_CONFIG_ENV" in output
        assert "(default)" not in output
