from __future__ import annotations

import time

import yaml

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric_scripts.cli.login.device_code import cmd_login_device_code


class TestCmdLoginDeviceCode:
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

        mock_dc = mocker.patch("bfabric_scripts.cli.login.device_code.device_code_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        cmd_login_device_code(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
        )
        mock_dc.assert_called_once()

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

        mocker.patch("bfabric_scripts.cli.login.device_code.device_code_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        cmd_login_device_code(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            set_default=False,
        )

        data = yaml.safe_load(config_file.read_text())
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
        mock_dc = mocker.patch("bfabric_scripts.cli.login.device_code.device_code_login", return_value=token)
        mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session)
        cmd_login_device_code(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="read-write-upload",
        )
        assert mock_dc.call_args.kwargs["scope"] == f"{DEFAULT_OAUTH_SCOPE} tus"
