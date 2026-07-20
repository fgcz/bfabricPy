from __future__ import annotations

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

    def test_prompts_for_default_when_omitted(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        # No --set-default given: in a terminal the user is asked; here they decline.
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
                    "EXISTING": {"base_url": "https://old.example.com", "auth_method": "oauth"},
                }
            )
        )
        mocker.patch("bfabric_scripts.cli.login.oauth_login.pkce_login", return_value=oauth_token)
        # No TTY (pytest) and no --config-env => reuse the current default env, not PRODUCTION.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_login(base_url="https://example.com/bfabric", client_id="c", config_file=config_file, scope="api:read")
        data = yaml.safe_load(config_file.read_text())
        assert data["EXISTING"]["base_url"] == "https://example.com/bfabric"
        assert "PRODUCTION" not in data
