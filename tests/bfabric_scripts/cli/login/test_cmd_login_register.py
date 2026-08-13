from __future__ import annotations

import json
import time

import pytest
import yaml

from bfabric_scripts.cli.login._constants import DEFAULT_REGISTRATION_SCOPE
from bfabric_scripts.cli.login.register import cmd_login_register


def seed_token_cache(base_url: str, env_name: str, access_token: str, *, client_id: str = "my-app") -> None:
    """Write a valid cached token where ``connect()`` looks for it (``$HOME`` is isolated per test)."""
    from bfabric.oauth import compute_token_cache_path

    path = compute_token_cache_path(base_url, client_id, env_name).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": "rt",
                "token_type": "Bearer",
                "expires_at": time.time() + 3600,
            }
        )
    )


class TestCmdLoginRegister:
    def test_prints_result_as_json(self, mocker, capsys):
        result = {"client_id": "new-client", "client_secret": "secret123"}
        mocker.patch("bfabric_scripts.cli.login.register.register_client", return_value=result)
        cmd_login_register(
            base_url="https://example.com/bfabric",
            token="bearer-tok",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            no_service_user=True,
        )
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out
        assert '"client_secret": "secret123"' in output.out
        # Warning should be printed when passing token via flag
        assert "insecure" in output.err

    def test_error_handling(self, mocker, capsys):
        mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            side_effect=RuntimeError("forbidden"),
        )
        try:
            cmd_login_register(
                base_url="https://example.com/bfabric",
                token="bad-tok",
                client_name="My App",
                redirect_uri="http://localhost/callback",
                no_service_user=True,
            )
        except SystemExit as e:
            assert e.code == 1
        err = capsys.readouterr().err
        assert "forbidden" in err

    def test_no_token_and_no_config_file_errors(self, tmp_path, capsys):
        """Without a token the command authenticates via ``connect()``, and surfaces its error."""
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                base_url="https://example.com/bfabric",
                client_name="My App",
                redirect_uri="http://localhost/callback",
                config_file=tmp_path / "missing.yml",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        assert "no config file found" in capsys.readouterr().err

    def test_base_url_required_without_config_env(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                token="bearer-tok",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "base_url is required" in err

    def test_uses_cached_token_from_config_env(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        base_url = "https://example.com/bfabric"
        client_id = "my-app"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": base_url,
                        "auth_method": "oauth",
                        "client_id": client_id,
                    },
                }
            )
        )

        seed_token_cache(base_url, "PROD", "cached-jwt", client_id=client_id)

        result = {"client_id": "new-client", "client_secret": "secret123"}
        mock_register = mocker.patch("bfabric_scripts.cli.login.register.register_client", return_value=result)
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            config_env="PROD",
            config_file=config_file,
            no_service_user=True,
        )
        mock_register.assert_called_once_with(
            base_url=base_url,
            token="cached-jwt",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            service_user=None,
            scope=DEFAULT_REGISTRATION_SCOPE,
            grant_types=None,
        )
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out

    def test_explicit_base_url_overrides_config(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://config-url.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "my-app",
                    },
                }
            )
        )

        seed_token_cache("https://config-url.com/bfabric", "PROD", "cached-jwt")

        result = {"client_id": "new-client", "client_secret": "secret123"}
        mock_register = mocker.patch("bfabric_scripts.cli.login.register.register_client", return_value=result)
        cmd_login_register(
            base_url="https://explicit-url.com/bfabric",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            config_env="PROD",
            config_file=config_file,
            no_service_user=True,
        )
        # Explicit base_url should win over config
        mock_register.assert_called_once_with(
            base_url="https://explicit-url.com/bfabric",
            token="cached-jwt",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            service_user=None,
            scope=DEFAULT_REGISTRATION_SCOPE,
            grant_types=None,
        )

    def test_config_env_missing_env(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "login": "user",
                        "password": "x" * 32,
                    },
                }
            )
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                config_env="NONEXISTENT",
                config_file=config_file,
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        assert "NONEXISTENT" in capsys.readouterr().err

    def test_config_env_non_oauth_sends_configured_password(self, tmp_path, mocker):
        """A password environment has no bearer token, so ``connect()`` yields the SOAP password.

        The server rejects it; the command does not pre-screen ``auth_method`` itself.
        """
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://example.com/bfabric",
                        "login": "user",
                        "password": "x" * 32,
                    },
                }
            )
        )
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            config_env="PROD",
            config_file=config_file,
            no_service_user=True,
        )
        assert mock_register.call_args.kwargs["token"] == "x" * 32


class TestCmdLoginRegisterServiceUserChoice:
    """``register`` requires the same explicit service-user choice as ``register-webapp``."""

    def test_requires_service_user_choice(self, mocker, capsys):
        mock_register = mocker.patch("bfabric_scripts.cli.login.register.register_client")
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                base_url="https://example.com/bfabric",
                token="tok",
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "--service-user" in err
        assert "--no-service-user" in err
        mock_register.assert_not_called()

    def test_rejects_service_user_and_no_service_user_together(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register(
                client_name="My App",
                redirect_uri="http://localhost/callback",
                base_url="https://example.com/bfabric",
                token="tok",
                service_user="trace",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        assert "mutually exclusive" in capsys.readouterr().err

    def test_no_service_user_registers_without_grant(self, mocker):
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            base_url="https://example.com/bfabric",
            token="tok",
            no_service_user=True,
        )
        assert mock_register.call_args.kwargs["service_user"] is None

    def test_service_user_is_forwarded(self, mocker):
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            base_url="https://example.com/bfabric",
            token="tok",
            service_user="trace",
        )
        assert mock_register.call_args.kwargs["service_user"] == "trace"


class TestCmdLoginRegisterResolvesEnvironment:
    """``register`` resolves the environment like every other ``auth`` command, instead of prompting."""

    @pytest.fixture
    def oauth_config_file(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://prod.example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "my-app",
                    },
                    "STAGE": {
                        "base_url": "https://stage.example.com/bfabric",
                        "auth_method": "oauth",
                        "client_id": "my-app",
                    },
                }
            )
        )
        return config_file

    @pytest.fixture
    def cached_tokens(self):
        """Seed the on-disk token cache for both environments, so each resolves to a distinct token."""
        seed_token_cache("https://prod.example.com/bfabric", "PROD", "prod-jwt")
        seed_token_cache("https://stage.example.com/bfabric", "STAGE", "stage-jwt")

    def test_uses_default_env_when_no_flags_given(self, oauth_config_file, cached_tokens, mocker):
        """The regression: a bare ``register`` used to demand a hand-pasted bearer token."""
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            config_file=oauth_config_file,
            no_service_user=True,
        )
        assert mock_register.call_args.kwargs["base_url"] == "https://prod.example.com/bfabric"
        assert mock_register.call_args.kwargs["token"] == "prod-jwt"

    def test_config_env_var_takes_precedence_over_default(self, oauth_config_file, cached_tokens, mocker, monkeypatch):
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "STAGE")
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            config_file=oauth_config_file,
            no_service_user=True,
        )
        assert mock_register.call_args.kwargs["base_url"] == "https://stage.example.com/bfabric"

    def test_explicit_config_env_beats_env_var_and_default(self, oauth_config_file, cached_tokens, mocker, monkeypatch):
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "PROD")
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            client_name="My App",
            redirect_uri="http://localhost/callback",
            config_env="STAGE",
            config_file=oauth_config_file,
            no_service_user=True,
        )
        assert mock_register.call_args.kwargs["base_url"] == "https://stage.example.com/bfabric"

    def test_explicit_token_still_skips_env_resolution(self, oauth_config_file, mocker, capsys):
        mock_register = mocker.patch(
            "bfabric_scripts.cli.login.register.register_client",
            return_value={"client_id": "new-client"},
        )
        cmd_login_register(
            base_url="https://explicit.example.com/bfabric",
            client_name="My App",
            redirect_uri="http://localhost/callback",
            token="flag-token",
            config_file=oauth_config_file,
            no_service_user=True,
        )
        assert mock_register.call_args.kwargs["token"] == "flag-token"
        assert "insecure" in capsys.readouterr().err
