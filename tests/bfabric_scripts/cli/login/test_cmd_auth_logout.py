from __future__ import annotations

import json

import pytest
import yaml

from bfabric_scripts.cli.login.manage import cmd_auth_logout


@pytest.fixture
def cache_path(tmp_path, mocker):
    """A token cache on disk, wired in as the path every environment resolves to."""
    path = tmp_path / "tok.json"
    path.write_text(json.dumps({"access_token": "t", "scope": "api:read"}))
    mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=path)
    return path


def _write_oauth_config(config_file, **extra):
    config_file.write_text(
        yaml.dump(
            {
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "auth_method": "oauth",
                    "client_id": "CLI",
                    "scope": "api:write tus",
                    **extra,
                },
            }
        )
    )


class TestOAuthLogout:
    def test_clears_the_token_cache(self, tmp_path, capsys, cache_path):
        config_file = tmp_path / "config.yml"
        _write_oauth_config(config_file)
        cmd_auth_logout(config_file=config_file)
        assert not cache_path.exists()
        assert "Cleared the cached OAuth token" in capsys.readouterr().out

    def test_keeps_the_login_recipe_so_a_zero_argument_login_still_works(self, tmp_path, cache_path):
        """The point of logout-vs-remove: a "configured but logged out" environment stays replayable."""
        config_file = tmp_path / "config.yml"
        _write_oauth_config(config_file)
        cmd_auth_logout(config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
        assert data["PROD"]["client_id"] == "CLI"
        assert data["PROD"]["scope"] == "api:write tus"
        assert data["GENERAL"]["default_config"] == "PROD"

    def test_states_that_the_token_is_not_revoked(self, tmp_path, capsys, cache_path):
        """Logout does not revoke server-side, so silence here would let the user believe otherwise.

        The notice describes what the command does, not what the server supports: instances do
        advertise a ``revocation_endpoint``, so a claim about B-Fabric's capabilities would be wrong.
        """
        config_file = tmp_path / "config.yml"
        _write_oauth_config(config_file)
        cmd_auth_logout(config_file=config_file)
        output = capsys.readouterr().out
        assert "does not revoke the token server-side" in output
        assert "until it expires" in output

    def test_reports_when_there_was_nothing_to_clear(self, tmp_path, capsys, mocker):
        config_file = tmp_path / "config.yml"
        _write_oauth_config(config_file)
        mocker.patch("bfabric_scripts.cli.login.manage.compute_token_cache_path", return_value=tmp_path / "absent.json")
        cmd_auth_logout(config_file=config_file)
        output = capsys.readouterr().out
        assert "No stored credentials found" in output
        # Nothing was removed, so the not-revoked caveat would be noise.
        assert "does not revoke" not in output


class TestPatLogout:
    def test_strips_the_pat_from_the_config_file(self, tmp_path, capsys):
        """Load-bearing: a cache-only implementation would report success while leaving the PAT in
        plaintext, because a PAT has no cache to clear."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "pat",
                        "pat": "secret-pat-token",
                    },
                }
            )
        )
        cmd_auth_logout(config_file=config_file)
        raw = config_file.read_text()
        assert "secret-pat-token" not in raw
        assert "pat" not in yaml.safe_load(raw)["PROD"]
        assert yaml.safe_load(raw)["PROD"]["base_url"] == "https://example.com/bfabric"
        assert "Removed pat" in capsys.readouterr().out


class TestPasswordLogout:
    def test_strips_login_and_password(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "login": "someone",
                        "password": "x" * 32,
                    },
                }
            )
        )
        cmd_auth_logout(config_file=config_file)
        env = yaml.safe_load(config_file.read_text())["PROD"]
        assert "login" not in env
        assert "password" not in env
        assert env["base_url"] == "https://example.com/bfabric"


class TestLogoutTargeting:
    def test_defaults_to_the_active_environment(self, tmp_path, cache_path):
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
        cmd_auth_logout(config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert "pat" not in data["PROD"]
        assert data["TEST"]["pat"] == "t"

    def test_honours_the_config_env_variable(self, tmp_path, monkeypatch, cache_path):
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
        cmd_auth_logout(config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["pat"] == "p"
        assert "pat" not in data["TEST"]

    def test_all_logs_out_of_every_environment(self, tmp_path, cache_path):
        """``--all`` exists so leaving nothing behind doesn't require enumerating environments first."""
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
        cmd_auth_logout(config_file=config_file, all_environments=True)
        data = yaml.safe_load(config_file.read_text())
        assert "pat" not in data["PROD"]
        assert "pat" not in data["TEST"]

    def test_unknown_environment_is_reported(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        _write_oauth_config(config_file)
        cmd_auth_logout("NOPE", config_file=config_file)
        assert "not found" in capsys.readouterr().out

    def test_missing_config_file(self, tmp_path, capsys):
        cmd_auth_logout(config_file=tmp_path / "nonexistent.yml")
        assert "not found" in capsys.readouterr().out

    def test_refuses_under_a_config_override(self, tmp_path, monkeypatch, capsys, cache_path):
        config_file = tmp_path / "config.yml"
        _write_oauth_config(config_file)
        monkeypatch.setenv("BFABRICPY_CONFIG_OVERRIDE", '{"base_url": "https://example.com"}')
        cmd_auth_logout(config_file=config_file)
        assert cache_path.exists()
        assert "BFABRICPY_CONFIG_OVERRIDE" in capsys.readouterr().out
