from __future__ import annotations

import json
import time

import pytest
import yaml

from bfabric_scripts.cli.login._constants import SCOPE_PRESETS_BY_NAME
from bfabric_scripts.cli.login.oauth_login import cmd_auth_login


class TestCmdAuthLogin:
    def test_writes_config_and_caches_token(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            scope="api:read",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
        )
        mock_pkce.assert_called_once()

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "oauth"
        assert data["PROD"]["client_id"] == "test-client"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_records_the_requested_scope(self, tmp_path, mocker, oauth_token, oauth_session):
        """The scope is what a later zero-argument login replays, so it has to reach the config."""
        config_file = tmp_path / "config.yml"
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            scope="upload",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
        )
        assert yaml.safe_load(config_file.read_text())["PROD"]["scope"] == "api:write tus"

    def test_set_default_false_does_not_set_default(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            scope="api:read",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            set_default=False,
        )

        data = yaml.safe_load(config_file.read_text())
        assert "default_config" not in data["GENERAL"]
        assert data["PROD"]["auth_method"] == "oauth"

    def test_prompts_for_default_on_a_new_environment(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        # No --set-default given: for a new environment the user is asked; here they decline.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=False)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="read-write",
        )
        confirm.assert_called_once()
        data = yaml.safe_load(config_file.read_text())
        # Declining the prompt means the environment is not made the default.
        assert "default_config" not in data["GENERAL"]
        assert data["PROD"]["auth_method"] == "oauth"

    def test_cancel_at_set_default_aborts(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        # No --set-default given: the user reaches the confirm prompt and cancels it (Ctrl-C -> None).
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=None)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="read-write",
        )
        # Cancelling aborts the whole login: no browser flow, no config written.
        mock_pkce.assert_not_called()
        assert not config_file.exists()
        assert "Login aborted." in capsys.readouterr().err

    def test_scope_preset_is_expanded(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="upload",
        )
        # The preset name expands to the real scope string requested from the OAuth flow.
        assert mock_pkce.call_args.kwargs["scope"] == SCOPE_PRESETS_BY_NAME["upload"].scope

    def test_config_env_omitted_falls_back_to_current_default(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "EXISTING"},
                    "EXISTING": {"base_url": "https://example.com/bfabric", "auth_method": "oauth"},
                }
            )
        )
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_login(client_id="c", config_file=config_file, scope="api:read")
        data = yaml.safe_load(config_file.read_text())
        assert data["EXISTING"]["scope"] == "api:read"
        assert "PRODUCTION" not in data

    def test_no_browser_is_passed_through(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        cmd_auth_login(
            base_url="https://example.com/bfabric",
            scope="api:read",
            config_env="PROD",
            config_file=config_file,
            no_browser=True,
        )
        assert mock_pkce.call_args.kwargs["open_browser"] is False

    def test_refuses_to_run_under_a_config_override(self, tmp_path, mocker, monkeypatch, capsys):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        monkeypatch.setenv("BFABRICPY_CONFIG_OVERRIDE", '{"base_url": "https://example.com"}')
        cmd_auth_login(base_url="https://example.com/bfabric", scope="api:read", config_file=config_file)
        mock_pkce.assert_not_called()
        assert not config_file.exists()
        assert "BFABRICPY_CONFIG_OVERRIDE" in capsys.readouterr().out


class TestZeroArgumentReLogin:
    """The headline fix: a recorded environment is a replayable login recipe."""

    def _write_env(self, config_file, **extra):
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

    def test_replays_recorded_base_url_and_scope_without_prompting(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        self._write_env(config_file, scope="api:write tus")
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        # A terminal is available, so any prompt *would* fire — there must simply be none to fire.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        select_choice = mocker.patch("bfabric_scripts.cli.login._common.select_choice")
        select_or_input = mocker.patch("bfabric_scripts.cli.login._common.select_or_input")
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")

        cmd_auth_login(config_file=config_file)

        assert mock_pkce.call_args.args[0] == "https://example.com/bfabric"
        assert mock_pkce.call_args.kwargs["scope"] == "api:write tus"
        select_choice.assert_not_called()
        select_or_input.assert_not_called()
        confirm.assert_not_called()

    def test_reports_the_scope_being_reused(self, tmp_path, mocker, capsys, oauth_token, oauth_session):
        """Someone who once picked read-only has to be able to notice on a silent re-login."""
        config_file = tmp_path / "config.yml"
        self._write_env(config_file, scope="api:read")
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_login(config_file=config_file)
        assert "Requesting scope: api:read" in capsys.readouterr().err

    def test_environment_without_a_recorded_scope_prompts_once_and_records_it(
        self, tmp_path, mocker, oauth_token, oauth_session
    ):
        """A 1.16.0-era environment: prompt rather than reuse the cached *granted* scope, then record
        the answer so the next run is prompt-free."""
        config_file = tmp_path / "config.yml"
        self._write_env(config_file)
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        select_choice = mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value="read-write")

        cmd_auth_login(config_file=config_file)

        select_choice.assert_called_once()
        assert mock_pkce.call_args.kwargs["scope"] == "api:write"
        assert yaml.safe_load(config_file.read_text())["PROD"]["scope"] == "api:write"

        # Second run: the recorded scope is replayed, so nothing is asked.
        select_choice.reset_mock()
        cmd_auth_login(config_file=config_file)
        select_choice.assert_not_called()

    def test_headless_environment_without_a_scope_aborts(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        self._write_env(config_file)
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_login(config_file=config_file)
        mock_pkce.assert_not_called()
        assert "Pass --scope" in capsys.readouterr().err

    def test_preserves_unrelated_environment_keys(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        self._write_env(config_file, scope="api:read", application_ids={"app": 7}, engine="ZEEP")
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_login(config_file=config_file)
        env = yaml.safe_load(config_file.read_text())["PROD"]
        assert env["application_ids"] == {"app": 7}
        assert env["engine"] == "ZEEP"


class TestRepointGuard:
    def _write_env(self, config_file):
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://prod.example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "CLI",
                        "scope": "api:read",
                    },
                }
            )
        )

    def test_refuses_to_repoint_non_interactively(self, tmp_path, mocker, capsys):
        """Previously a re-login silently overwrote the default environment's base_url, which could
        point PRODUCTION at a test host without asking."""
        config_file = tmp_path / "config.yml"
        self._write_env(config_file)
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.is_interactive", return_value=False)

        cmd_auth_login(base_url="https://test.example.com/bfabric", config_file=config_file, scope="api:read")

        mock_pkce.assert_not_called()
        assert yaml.safe_load(config_file.read_text())["PROD"]["base_url"] == "https://prod.example.com/bfabric"
        assert "Refusing to repoint" in capsys.readouterr().err

    def test_repoints_when_confirmed(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        self._write_env(config_file)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.confirm", return_value=True)

        cmd_auth_login(base_url="https://test.example.com/bfabric", config_file=config_file, scope="api:read")

        assert yaml.safe_load(config_file.read_text())["PROD"]["base_url"] == "https://test.example.com/bfabric"

    def test_declining_aborts_without_writing(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        self._write_env(config_file)
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.confirm", return_value=False)

        cmd_auth_login(base_url="https://test.example.com/bfabric", config_file=config_file, scope="api:read")

        mock_pkce.assert_not_called()
        assert yaml.safe_load(config_file.read_text())["PROD"]["base_url"] == "https://prod.example.com/bfabric"
        assert "Login aborted." in capsys.readouterr().err

    def test_same_url_is_not_treated_as_a_repoint(self, tmp_path, mocker, oauth_token, oauth_session):
        """A trailing slash or a bare host is the same instance, so it must not trigger a prompt."""
        config_file = tmp_path / "config.yml"
        self._write_env(config_file)
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        confirm = mocker.patch("bfabric_scripts.cli.login.oauth_login.confirm")
        cmd_auth_login(base_url="https://prod.example.com/bfabric/", config_file=config_file, scope="api:read")
        confirm.assert_not_called()


class TestFirstLogin:
    def test_picks_an_instance_and_derives_the_environment_name(self, tmp_path, mocker, oauth_token, oauth_session):
        """Mode A: nothing configured yet, and no environment name to invent."""
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        select_or_input = mocker.patch("bfabric_scripts.cli.login._common.select_or_input")
        mocker.patch(
            "bfabric_scripts.cli.login._common.select_choice",
            side_effect=["fgcz-demo", "read-only"],
        )
        mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=True)

        cmd_auth_login(config_file=config_file)

        # The environment name is derived from the picked instance, never asked for.
        select_or_input.assert_not_called()
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "fgcz-demo"
        assert data["fgcz-demo"]["base_url"] == "https://fgcz-bfabric-demo.uzh.ch/bfabric"
        assert data["fgcz-demo"]["scope"] == "api:read"
        assert mock_pkce.call_args.args[0] == "https://fgcz-bfabric-demo.uzh.ch/bfabric"

    def test_headless_first_login_needs_a_url(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_login(config_file=config_file, scope="api:read")
        mock_pkce.assert_not_called()
        assert "Pass the instance URL" in capsys.readouterr().err


class TestBaseUrl:
    def test_normalizes_a_bare_host_before_the_browser_opens(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        cmd_auth_login(
            base_url="fgcz-bfabric-demo.uzh.ch",
            config_env="demo",
            config_file=config_file,
            scope="api:read",
        )
        assert mock_pkce.call_args.args[0] == "https://fgcz-bfabric-demo.uzh.ch/bfabric"

    def test_rejects_a_non_http_url(self, tmp_path, mocker, capsys):
        """A typo is reported as rejected input, not as a traceback."""
        config_file = tmp_path / "config.yml"
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login")
        cmd_auth_login(base_url="ftp://example.com", config_env="PROD", config_file=config_file, scope="api:read")
        mock_pkce.assert_not_called()
        assert not config_file.exists()
        err = capsys.readouterr().err
        assert "http or https" in err
        assert "Login aborted." in err
