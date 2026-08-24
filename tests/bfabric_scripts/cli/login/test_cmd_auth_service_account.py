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
