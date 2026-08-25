from __future__ import annotations

import base64
import json
import time

import yaml

from bfabric_scripts.cli.login._constants import SCOPE_PRESETS_BY_NAME
from bfabric_scripts.cli.login.manage import cmd_auth_list, cmd_auth_status, describe_scope, describe_token_cache


class TestCmdAuthStatus:
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
        cmd_auth_status(config_file=config_file)
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
                        "scope": SCOPE_PRESETS_BY_NAME["upload"].scope,
                    },
                }
            )
        )
        cmd_auth_status(config_file=config_file)
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
        cmd_auth_status(config_file=config_file)
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
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=tmp_path / "absent.json")
        cmd_auth_status(config_file=config_file)
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
                        "scope": SCOPE_PRESETS_BY_NAME["upload"].scope,
                    },
                }
            )
        )
        cache_path = tmp_path / "tok.json"
        cache_path.write_text(
            json.dumps(
                {
                    "access_token": "x",
                    "scope": SCOPE_PRESETS_BY_NAME["upload"].scope,
                    "expires_at": time.time() + 9000,
                }
            )
        )
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=cache_path)
        cmd_auth_status(config_file=config_file)
        output = capsys.readouterr().out
        # The recorded scope matches the upload preset and the token is still valid.
        assert "upload" in output
        assert "expires in" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_auth_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "not found" in output


class TestDescribeScope:
    def test_matched_preset_is_annotated(self):
        # A granted scope equal to a preset (order-insensitive) is annotated with the preset name.
        scope = "tus api:write"  # reordered to prove match is order-insensitive
        described = describe_scope(scope)
        assert "upload" in described
        assert "tus" in described

    def test_unmatched_scope_shown_raw(self):
        assert describe_scope("api:read custom:thing") == "api:read custom:thing"

    def test_absent_scope_is_not_recorded(self):
        assert describe_scope(None) == "(not recorded)"
        assert describe_scope("") == "(not recorded)"
        assert describe_scope("   ") == "(not recorded)"


class TestDescribeTokenCache:
    def test_missing_cache(self):
        assert describe_token_cache(None, now=1000.0) == "missing"

    def test_present_without_expiry(self):
        assert describe_token_cache({"access_token": "x"}, now=1000.0) == "present"

    def test_expired(self):
        assert "expired" in describe_token_cache({"access_token": "x", "expires_at": 900}, now=1000.0)

    def test_valid_reports_remaining(self):
        # 2h30m from now.
        described = describe_token_cache({"access_token": "x", "expires_at": 1000 + 9000}, now=1000.0)
        assert "present" in described
        assert "2h" in described


class TestStatusDisplay:
    def _write(self, config_file, **extra):
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "CLI",
                        **extra,
                    },
                }
            )
        )

    def _cache(self, tmp_path, mocker, claims, **extra):
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        cache_path = tmp_path / "tok.json"
        cache_path.write_text(json.dumps({"access_token": f"h.{payload}.s", **extra}))
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=cache_path)
        return cache_path

    def test_shows_the_requested_scope_from_the_config(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        self._write(config_file, scope="api:write tus")
        self._cache(tmp_path, mocker, {"sub": "someone"}, scope="api:write tus")
        cmd_auth_status(config_file=config_file)
        output = capsys.readouterr().out
        assert "api:write tus" in output
        assert "upload" in output

    def test_annotates_the_active_reason(self, tmp_path, capsys, mocker, monkeypatch):
        config_file = tmp_path / "config.yml"
        self._write(config_file, scope="api:read")
        self._cache(tmp_path, mocker, {"sub": "someone"}, scope="api:read")
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "PROD")
        cmd_auth_status(config_file=config_file)
        assert "active via BFABRICPY_CONFIG_ENV" in capsys.readouterr().out

    def test_config_env_variable_selects_the_environment(self, tmp_path, capsys, monkeypatch, mocker):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {"base_url": "https://prod.example.com/bfabric", "auth_method": "pat", "pat": "p"},
                    "TEST": {"base_url": "https://test.example.com/bfabric", "auth_method": "pat", "pat": "t"},
                }
            )
        )
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "TEST")
        cmd_auth_status(config_file=config_file)
        assert "test.example.com" in capsys.readouterr().out


class TestUnsupportedAuthMethod:
    """An auth_method this version does not know is reported, not silently discarded."""

    def _write(self, config_file):
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "some_future_method",
                        "client_id": "CLI",
                    },
                    "OTHER": {
                        "base_url": "https://other.example.com/bfabric",
                        "login": "testuser",
                        "password": "x" * 32,
                    },
                }
            )
        )

    def test_status_names_the_method_and_says_to_upgrade(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        self._write(config_file)

        cmd_auth_status(config_file=config_file)

        output = capsys.readouterr().out
        assert "some_future_method" in output
        assert "upgrade" in output.lower()

    def test_unrelated_environment_is_still_listed(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        self._write(config_file)

        cmd_auth_list(config_file=config_file)

        output = capsys.readouterr().out
        assert "OTHER" in output
        assert "password" in output
