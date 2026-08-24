from __future__ import annotations

import pytest

from bfabric_scripts.cli.login.register_webapp import cmd_login_register_webapp


class TestCmdLoginRegisterWebapp:
    def test_requires_service_user_choice(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(app_name="My App", web_url="http://localhost:8060")
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "--service-user" in err
        assert "--no-service-user" in err

    def test_rejects_service_user_and_no_service_user_together(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(
                app_name="My App",
                web_url="http://localhost:8060",
                service_user="trace",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "mutually exclusive" in err

    def test_no_service_user_passes_validation(self, mocker, capsys):
        mocker.patch(
            "bfabric.Bfabric.connect",
            side_effect=RuntimeError("connect failed"),
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(
                app_name="My App",
                web_url="http://localhost:8060",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Could not connect to B-Fabric" in err

    def test_service_user_passes_validation(self, mocker, capsys):
        mocker.patch(
            "bfabric.Bfabric.connect",
            side_effect=RuntimeError("connect failed"),
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(
                app_name="My App",
                web_url="http://localhost:8060",
                service_user="trace",
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Could not connect to B-Fabric" in err


class TestSaveRegistrationWebapp:
    """``--save-env`` records the webapp's client so its registration can be corrected later."""

    @staticmethod
    def _mock_register(mocker, *, with_secret: bool = True):
        oauth: dict[str, object] = {
            "id": 42,
            "client_id": "webapp-client",
            "registration_access_token": "reg-tok",
            "registration_client_uri": "https://example.com/bfabric/rest/oauth/register/webapp-client",
        }
        if with_secret:
            oauth["client_secret"] = "s3cret"
        mocker.patch(
            "bfabric.oauth.register_webapp",
            return_value={"oauth": oauth, "application": mocker.MagicMock()},
        )
        client = mocker.MagicMock()
        client.config.base_url = "https://example.com/bfabric"
        client.auth.password.get_secret_value.return_value = "bearer-tok"
        mocker.patch("bfabric.Bfabric.connect", return_value=client)

    def test_saves_registration_credentials(self, mocker, tmp_path):
        import yaml

        self._mock_register(mocker)
        config_file = tmp_path / "config.yml"
        cmd_login_register_webapp(
            app_name="My App",
            web_url="https://app.example.com",
            service_user="svc",
            config_file=config_file,
            save_env="APP",
        )
        env = yaml.safe_load(config_file.read_text())["APP"]
        assert env["client_id"] == "webapp-client"
        assert env["registration_access_token"] == "reg-tok"
        assert env["registration_client_uri"] == "https://example.com/bfabric/rest/oauth/register/webapp-client"
        # No auth_method: a webapp's users log in interactively, so the environment must not be
        # rerouted through the stored secret. See TestWebappSaveEnvAuthMethod.
        assert "auth_method" not in env
        assert env["base_url"] == "https://example.com/bfabric"

    def test_does_not_write_without_save_env(self, mocker, tmp_path):
        self._mock_register(mocker)
        config_file = tmp_path / "config.yml"
        cmd_login_register_webapp(
            app_name="My App",
            web_url="https://app.example.com",
            service_user="svc",
            config_file=config_file,
        )
        assert not config_file.exists()

    def test_no_service_user_records_no_auth_method(self, mocker, tmp_path):
        """Without the client_credentials grant the stored client cannot authenticate."""
        import yaml

        self._mock_register(mocker, with_secret=False)
        config_file = tmp_path / "config.yml"
        cmd_login_register_webapp(
            app_name="My App",
            web_url="https://app.example.com",
            no_service_user=True,
            config_file=config_file,
            save_env="APP",
        )
        env = yaml.safe_load(config_file.read_text())["APP"]
        assert "auth_method" not in env
        assert env["registration_access_token"] == "reg-tok"


class TestWebappSaveEnvAuthMethod:
    """A webapp environment must not be stamped as a service account: its users log in through the
    browser, and `auth_method: client_credentials` would silently reroute every later connect()."""

    @staticmethod
    def _mock(mocker, oauth):
        mocker.patch(
            "bfabric.oauth.register_webapp",
            return_value={"oauth": oauth, "application": mocker.MagicMock()},
        )
        client = mocker.MagicMock()
        client.config.base_url = "https://example.com/bfabric"
        client.auth.password.get_secret_value.return_value = "bearer-tok"
        mocker.patch("bfabric.Bfabric.connect", return_value=client)

    def test_service_user_webapp_does_not_stamp_client_credentials(self, mocker, tmp_path):
        import yaml

        self._mock(
            mocker,
            {
                "id": 42,
                "client_id": "webapp-client",
                "client_secret": "s3cret",
                "registration_access_token": "reg-tok",
                "registration_client_uri": "https://example.com/bfabric/rest/oauth/register/webapp-client",
            },
        )
        config_file = tmp_path / "config.yml"
        cmd_login_register_webapp(
            app_name="My App",
            web_url="https://app.example.com",
            service_user="svc",
            config_file=config_file,
            save_env="APP",
        )
        env = yaml.safe_load(config_file.read_text())["APP"]
        assert "auth_method" not in env
        # The credentials are still recorded so the client stays manageable.
        assert env["registration_access_token"] == "reg-tok"
        assert env["client_secret"] == "s3cret"


class TestWebappSaveEnvMissingRegistrationKeys:
    """If the server omits the registration credentials, say so — the help text promises the
    redirect URI can be fixed later, and otherwise that fails only at client-update time."""

    @staticmethod
    def _mock(mocker, oauth):
        mocker.patch(
            "bfabric.oauth.register_webapp",
            return_value={"oauth": oauth, "application": mocker.MagicMock()},
        )
        client = mocker.MagicMock()
        client.config.base_url = "https://example.com/bfabric"
        client.auth.password.get_secret_value.return_value = "bearer-tok"
        mocker.patch("bfabric.Bfabric.connect", return_value=client)

    def test_warns_when_registration_credentials_absent(self, mocker, tmp_path, capsys):
        self._mock(mocker, {"id": 42, "client_id": "webapp-client"})
        config_file = tmp_path / "config.yml"
        cmd_login_register_webapp(
            app_name="My App",
            web_url="https://app.example.com",
            no_service_user=True,
            config_file=config_file,
            save_env="APP",
        )
        err = capsys.readouterr().err
        assert "registration" in err.lower()
        assert "client-update" in err

    def test_no_warning_when_present(self, mocker, tmp_path, capsys):
        self._mock(
            mocker,
            {
                "id": 42,
                "client_id": "webapp-client",
                "registration_access_token": "reg-tok",
                "registration_client_uri": "https://example.com/bfabric/rest/oauth/register/webapp-client",
            },
        )
        config_file = tmp_path / "config.yml"
        cmd_login_register_webapp(
            app_name="My App",
            web_url="https://app.example.com",
            no_service_user=True,
            config_file=config_file,
            save_env="APP",
        )
        assert "cannot be edited" not in capsys.readouterr().err
