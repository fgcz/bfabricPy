from __future__ import annotations

import time

import yaml

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric_scripts.cli.login.pkce import cmd_login_pkce


class TestCmdLoginPkce:
    def test_writes_config_and_caches_token(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        token = {
            "access_token": "jwt123",
            "refresh_token": "rt456",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }

        mock_session = mocker.MagicMock()
        mock_session.token = None
        mock_session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}

        mock_pkce = mocker.patch("bfabric_scripts.cli.login.pkce.pkce_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        cmd_login_pkce(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
        )
        mock_pkce.assert_called_once()

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "oauth"
        assert data["PROD"]["client_id"] == "test-client"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_set_default_false_does_not_set_default(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        token = {
            "access_token": "jwt123",
            "refresh_token": "rt456",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        mock_session = mocker.MagicMock()
        mock_session.token = None
        mock_session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}

        mocker.patch("bfabric_scripts.cli.login.pkce.pkce_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        cmd_login_pkce(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            set_default=False,
        )

        data = yaml.safe_load(config_file.read_text())
        assert "default_config" not in data["GENERAL"]
        assert data["PROD"]["auth_method"] == "oauth"

    def test_prompts_for_default_when_omitted(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        token = {
            "access_token": "jwt123",
            "refresh_token": "rt456",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        mock_session = mocker.MagicMock()
        mock_session.token = None
        mock_session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}
        mocker.patch("bfabric_scripts.cli.login.pkce.pkce_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        # No --set-default given: in a terminal the user is asked; here they decline.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=False)
        cmd_login_pkce(
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

    def test_scope_preset_is_expanded(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        token = {
            "access_token": "jwt123",
            "refresh_token": "rt456",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        mock_session = mocker.MagicMock()
        mock_session.token = None
        mock_session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}
        mock_pkce = mocker.patch("bfabric_scripts.cli.login.pkce.pkce_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        cmd_login_pkce(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="read-write-upload",
        )
        # The preset name expands to the real scope string requested from the OAuth flow.
        assert mock_pkce.call_args.kwargs["scope"] == f"{DEFAULT_OAUTH_SCOPE} tus"

    def test_config_env_omitted_falls_back_to_current_default(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "EXISTING"},
                    "EXISTING": {"base_url": "https://old.example.com", "auth_method": "oauth"},
                }
            )
        )
        token = {
            "access_token": "jwt123",
            "refresh_token": "rt456",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        mock_session = mocker.MagicMock()
        mock_session.token = None
        mock_session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}
        mocker.patch("bfabric_scripts.cli.login.pkce.pkce_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        # No TTY (pytest) and no --config-env => reuse the current default env, not PRODUCTION.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_login_pkce(base_url="https://example.com/bfabric", client_id="c", config_file=config_file)
        data = yaml.safe_load(config_file.read_text())
        assert data["EXISTING"]["base_url"] == "https://example.com/bfabric"
        assert "PRODUCTION" not in data
