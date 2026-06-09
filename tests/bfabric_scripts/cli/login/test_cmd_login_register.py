from __future__ import annotations

import json
import time

import pytest
import yaml
from unittest.mock import patch, MagicMock

from bfabric_scripts.cli.login.register import cmd_login_register


class TestCmdLoginRegister:
    def test_prints_result_as_json(self, capsys):
        result = {"client_id": "new-client", "client_secret": "secret123"}
        with patch("bfabric_scripts.cli.login.register.register_client", return_value=result):
            cmd_login_register(
                base_url="https://example.com/bfabric",
                token="bearer-tok",
                client_name="My App",
                redirect_uri="http://localhost/callback",
            )
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out
        assert '"client_secret": "secret123"' in output.out
        # Warning should be printed when passing token via flag
        assert "insecure" in output.err

    def test_error_handling(self, capsys):
        with patch("bfabric_scripts.cli.login.register.register_client", side_effect=RuntimeError("forbidden")):
            try:
                cmd_login_register(
                    base_url="https://example.com/bfabric",
                    token="bad-tok",
                    client_name="My App",
                    redirect_uri="http://localhost/callback",
                )
            except SystemExit as e:
                assert e.code == 1
        err = capsys.readouterr().err
        assert "forbidden" in err

    def test_prompts_when_token_omitted(self, capsys):
        result = {"client_id": "new-client", "client_secret": "secret123"}
        with (
            patch("bfabric_scripts.cli.login.register.register_client", return_value=result),
            patch("bfabric_scripts.cli.login.register.getpass.getpass", return_value="prompted-token") as mock_getpass,
        ):
            cmd_login_register(
                base_url="https://example.com/bfabric",
                client_name="My App",
                redirect_uri="http://localhost/callback",
            )
        mock_getpass.assert_called_once()
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out

    def test_base_url_required_without_config_env(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                token="bearer-tok",
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "base_url is required" in err

    def test_uses_cached_token_from_config_env(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        base_url = "https://example.com/bfabric"
        client_id = "my-app"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": base_url,
                    "auth_method": "oauth",
                    "client_id": client_id,
                },
            })
        )

        mock_session = MagicMock()
        mock_session.token = {
            "access_token": "cached-jwt",
            "refresh_token": "rt",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        mock_session.metadata = {"token_endpoint": f"{base_url}/rest/oauth/token"}

        result = {"client_id": "new-client", "client_secret": "secret123"}
        with (
            patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session),
            patch("bfabric_scripts.cli.login.register.register_client", return_value=result) as mock_register,
        ):
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                config_env="PROD",
                config_file=config_file,
            )
        mock_register.assert_called_once_with(
            base_url=base_url,
            token="cached-jwt",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            service_user=None,
            scope="api:read api:write",
            grant_types=None,
        )
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out

    def test_explicit_base_url_overrides_config(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://config-url.com/bfabric",
                    "auth_method": "oauth",
                    "client_id": "my-app",
                },
            })
        )

        mock_session = MagicMock()
        mock_session.token = {
            "access_token": "cached-jwt",
            "refresh_token": "rt",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        mock_session.metadata = {"token_endpoint": "https://config-url.com/bfabric/rest/oauth/token"}

        result = {"client_id": "new-client", "client_secret": "secret123"}
        with (
            patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session),
            patch("bfabric_scripts.cli.login.register.register_client", return_value=result) as mock_register,
        ):
            cmd_login_register(
                base_url="https://explicit-url.com/bfabric",
                client_name="My App",
                redirect_uri="http://localhost/callback",
                config_env="PROD",
                config_file=config_file,
            )
        # Explicit base_url should win over config
        mock_register.assert_called_once_with(
            base_url="https://explicit-url.com/bfabric",
            token="cached-jwt",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            service_user=None,
            scope="api:read api:write",
            grant_types=None,
        )

    def test_config_env_missing_env(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "login": "user",
                    "password": "x" * 32,
                },
            })
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                config_env="NONEXISTENT",
                config_file=config_file,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "not found" in err

    def test_config_env_non_oauth(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "login": "user",
                    "password": "x" * 32,
                },
            })
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                config_env="PROD",
                config_file=config_file,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "does not use OAuth" in err
