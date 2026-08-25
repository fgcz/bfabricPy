from __future__ import annotations

import yaml

from bfabric_scripts.cli.login.service_account import cmd_auth_service_account


class TestCmdAuthServiceAccount:
    def test_writes_config_with_flags(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="sysadmin-cron",
            client_secret="s3cret",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert data["PROD"]["auth_method"] == "client_credentials"
        assert data["PROD"]["client_id"] == "sysadmin-cron"
        assert data["PROD"]["client_secret"] == "s3cret"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
        # Old-client-safety contract, as for PAT: never inline the secret where a <=1.19.0
        # client would try to validate it as a 32-char password.
        assert "login" not in data["PROD"]
        assert "password" not in data["PROD"]
        assert "insecure" in capsys.readouterr().err

    def test_prompts_when_secret_omitted(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        mocker.patch(
            "bfabric_scripts.cli.login.service_account.getpass.getpass",
            return_value="prompted-secret",
        )
        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["client_secret"] == "prompted-secret"

    def test_strips_trailing_slash(self, tmp_path):
        config_file = tmp_path / "config.yml"
        cmd_auth_service_account(
            base_url="https://example.com/bfabric/",
            client_id="cron",
            client_secret="s3cret",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_records_scope_when_given(self, tmp_path):
        config_file = tmp_path / "config.yml"
        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            client_secret="s3cret",
            scope="read-write",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["scope"] == "read-write"

    def test_second_env_does_not_disturb_the_first(self, tmp_path):
        """Two instances coexist: each keeps its own client_id and secret."""
        config_file = tmp_path / "config.yml"
        cmd_auth_service_account(
            base_url="https://prod.example.com/bfabric",
            client_id="prod-cron",
            client_secret="prod-secret",
            config_env="PROD",
            config_file=config_file,
            set_default=True,
        )
        cmd_auth_service_account(
            base_url="https://test.example.com/bfabric",
            client_id="test-cron",
            client_secret="test-secret",
            config_env="TEST",
            config_file=config_file,
            set_default=False,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["client_secret"] == "prod-secret"
        assert data["TEST"]["client_secret"] == "test-secret"
        assert data["GENERAL"]["default_config"] == "PROD"


class TestRotateSecretIntoExistingEnvironment:
    """Re-running the command is how a UI-rotated secret gets in; it must not strip the rest."""

    @staticmethod
    def _seed(tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "GENERAL:\n"
            "  default_config: CRON\n"
            "CRON:\n"
            "  base_url: https://example.com/bfabric\n"
            "  auth_method: client_credentials\n"
            "  client_id: cron-cid\n"
            "  client_secret: OLD-SECRET\n"
            "  scope: api:write\n"
            "  registration_access_token: reg-tok\n"
            "  registration_client_uri: https://example.com/bfabric/rest/oauth/register/cron-cid\n"
        )
        return config_file

    def test_updates_secret_and_keeps_registration_credentials(self, tmp_path):
        import yaml

        config_file = self._seed(tmp_path)
        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron-cid",
            client_secret="NEW-SECRET",
            config_env="CRON",
            config_file=config_file,
            set_default=False,
        )
        env = yaml.safe_load(config_file.read_text())["CRON"]
        assert env["client_secret"] == "NEW-SECRET"
        assert env["registration_access_token"] == "reg-tok"
        assert env["registration_client_uri"] == "https://example.com/bfabric/rest/oauth/register/cron-cid"
        assert env["scope"] == "api:write"
        assert env["client_id"] == "cron-cid"

    def test_explicit_scope_overrides_the_recorded_one(self, tmp_path):
        import yaml

        config_file = self._seed(tmp_path)
        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron-cid",
            client_secret="NEW-SECRET",
            scope="api:read",
            config_env="CRON",
            config_file=config_file,
            set_default=False,
        )
        assert yaml.safe_load(config_file.read_text())["CRON"]["scope"] == "api:read"


class TestOverwriteGuard:
    """Recording a service account rewrites ``auth_method``, so every later ``connect()`` on the
    environment authenticates as a different identity. Converting an existing login needs consent."""

    def _write_password_env(self, config_file):
        config_file.write_text(
            "GENERAL:\n"
            "  default_config: PROD\n"
            "PROD:\n"
            "  base_url: https://example.com/bfabric\n"
            "  login: someuser\n"
            "  password: " + "x" * 32 + "\n"
            "  auth_method: password\n"
        )

    def test_refuses_to_convert_an_existing_env_non_interactively(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        self._write_password_env(config_file)
        mocker.patch("bfabric_scripts.cli.login.service_account.is_interactive", return_value=False)

        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            client_secret="s3cret",
            config_env="PROD",
            config_file=config_file,
        )

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "password"
        assert "client_secret" not in data["PROD"]
        assert "--config-env" in capsys.readouterr().err

    def test_converts_when_confirmed(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        self._write_password_env(config_file)
        mocker.patch("bfabric_scripts.cli.login.service_account.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.service_account.confirm", return_value=True)

        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            client_secret="s3cret",
            config_env="PROD",
            config_file=config_file,
        )

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "client_credentials"
        assert data["PROD"]["client_secret"] == "s3cret"

    def test_declining_leaves_the_env_untouched(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        self._write_password_env(config_file)
        mocker.patch("bfabric_scripts.cli.login.service_account.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.service_account.confirm", return_value=False)

        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            client_secret="s3cret",
            config_env="PROD",
            config_file=config_file,
        )

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "password"
        assert data["PROD"]["login"] == "someuser"

    def test_drops_the_superseded_password_credentials(self, tmp_path, mocker):
        """A converted env's login/password can never authenticate again, so leaving them would
        strand an unreachable secret in the file."""
        config_file = tmp_path / "config.yml"
        self._write_password_env(config_file)
        mocker.patch("bfabric_scripts.cli.login.service_account.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login.service_account.confirm", return_value=True)

        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            client_secret="s3cret",
            config_env="PROD",
            config_file=config_file,
        )

        data = yaml.safe_load(config_file.read_text())
        assert "login" not in data["PROD"]
        assert "password" not in data["PROD"]

    def test_re_running_on_a_service_account_env_does_not_prompt(self, tmp_path, mocker):
        """Re-running is the documented way to store a rotated secret; it changes no identity."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "GENERAL:\n"
            "  default_config: PROD\n"
            "PROD:\n"
            "  base_url: https://example.com/bfabric\n"
            "  auth_method: client_credentials\n"
            "  client_id: cron\n"
            "  client_secret: old-secret\n"
            "  registration_access_token: rat\n"
            "  registration_client_uri: https://example.com/reg/cron\n"
        )
        mocker.patch("bfabric_scripts.cli.login.service_account.is_interactive", return_value=True)
        mock_confirm = mocker.patch("bfabric_scripts.cli.login.service_account.confirm")

        cmd_auth_service_account(
            base_url="https://example.com/bfabric",
            client_id="cron",
            client_secret="new-secret",
            config_env="PROD",
            config_file=config_file,
        )

        mock_confirm.assert_not_called()
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["client_secret"] == "new-secret"
        # The registration credentials must survive, or the client can no longer be edited.
        assert data["PROD"]["registration_access_token"] == "rat"
