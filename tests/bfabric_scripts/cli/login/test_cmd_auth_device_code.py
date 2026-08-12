from __future__ import annotations

import pytest
import yaml

from bfabric_scripts.cli.login._constants import SCOPE_PRESETS_BY_NAME
from bfabric_scripts.cli.login.oauth_login import cmd_auth_device_code


class TestCmdAuthDeviceCode:
    def test_writes_config_and_caches_token(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mock_dc = mocker.patch("bfabric_scripts.cli.login.oauth_login.device_code_login", return_value=oauth_token)
        cmd_auth_device_code(
            base_url="https://example.com/bfabric",
            scope="api:read",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
        )
        mock_dc.assert_called_once()

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "oauth"
        assert data["PROD"]["client_id"] == "test-client"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_set_default_false_does_not_set_default(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mocker.patch("bfabric_scripts.cli.login.oauth_login.device_code_login", return_value=oauth_token)
        cmd_auth_device_code(
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

    def test_cancel_at_set_default_aborts(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        mock_dc = mocker.patch("bfabric_scripts.cli.login.oauth_login.device_code_login")
        # No --set-default given: the user reaches the confirm prompt and cancels it (Ctrl-C -> None).
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=None)
        cmd_auth_device_code(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="read-write",
        )
        # Cancelling aborts the whole login: no device-code flow, no config written.
        mock_dc.assert_not_called()
        assert not config_file.exists()
        assert "Login aborted." in capsys.readouterr().err

    def test_scope_preset_is_expanded(self, tmp_path, mocker, oauth_token, oauth_session):
        config_file = tmp_path / "config.yml"
        mock_dc = mocker.patch("bfabric_scripts.cli.login.oauth_login.device_code_login", return_value=oauth_token)
        cmd_auth_device_code(
            base_url="https://example.com/bfabric",
            client_id="test-client",
            config_env="PROD",
            config_file=config_file,
            scope="upload",
        )
        assert mock_dc.call_args.kwargs["scope"] == SCOPE_PRESETS_BY_NAME["upload"].scope

    def test_replays_a_recorded_environment_with_no_arguments(self, tmp_path, mocker, oauth_token, oauth_session):
        """The device-code flow shares parameter resolution, so it is zero-argument re-loginable too."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "CLI",
                        "scope": "api:write",
                    },
                }
            )
        )
        mock_dc = mocker.patch("bfabric_scripts.cli.login.oauth_login.device_code_login", return_value=oauth_token)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        cmd_auth_device_code(config_file=config_file)
        assert mock_dc.call_args.args[0] == "https://example.com/bfabric"
        assert mock_dc.call_args.kwargs["scope"] == "api:write"
