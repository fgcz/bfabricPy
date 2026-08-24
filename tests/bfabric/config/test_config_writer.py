from __future__ import annotations

import os
import stat

import pytest
import yaml
from pydantic import ValidationError

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_file import ConfigFile
from bfabric.config.config_writer import (
    clear_environment_credentials,
    remove_environment_from_config,
    set_default_config,
    write_environment_to_config,
)


class TestWriteEnvironmentToConfig:
    def test_creates_new_file(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"}, set_default=True)
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert data["PROD"]["base_url"] == "https://example.com"

    def test_sets_permissions(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"}, set_default=True)
        mode = stat.S_IMODE(os.stat(config_path).st_mode)
        assert mode == 0o600

    def test_tightens_permissions_on_existing_file(self, tmp_path):
        # A pre-existing config (e.g. created before OAuth support) may be group/world-readable.
        # os.open's mode argument is only honored when the file is *created*, so writing into an
        # existing file must explicitly tighten the permissions or a secret (e.g. a PAT) would be
        # written into a world-readable file.
        config_path = tmp_path / "config.yml"
        config_path.write_text("GENERAL: {}\n")
        config_path.chmod(0o644)
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "login": "__oauth__", "password": "secret-pat"},
            set_default=True,
        )
        mode = stat.S_IMODE(os.stat(config_path).st_mode)
        assert mode == 0o600

    def test_merges_with_existing(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "OLD"},
                    "OLD": {"base_url": "https://old.example.com"},
                }
            )
        )
        write_environment_to_config(config_path, "NEW", {"base_url": "https://new.example.com"}, set_default=True)
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "NEW"
        assert data["OLD"]["base_url"] == "https://old.example.com"
        assert data["NEW"]["base_url"] == "https://new.example.com"

    def test_overwrites_supplied_keys_of_existing_env(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://v1.example.com"}, set_default=True)
        write_environment_to_config(config_path, "PROD", {"base_url": "https://v2.example.com"}, set_default=True)
        data = yaml.safe_load(config_path.read_text())
        assert data["PROD"]["base_url"] == "https://v2.example.com"

    def test_preserves_unrelated_keys_of_existing_env(self, tmp_path):
        """A re-login must not wipe hand-written keys the CLI knows nothing about."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://v1.example.com",
                        "application_ids": {"app": 123},
                        "job_notification_emails": "me@example.com",
                    },
                }
            )
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://v2.example.com", "auth_method": "oauth", "client_id": "CLI"},
            set_default=True,
        )
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert env["application_ids"] == {"app": 123}
        assert env["job_notification_emails"] == "me@example.com"
        assert env["base_url"] == "https://v2.example.com"

    def test_drops_stale_pat_when_re_login_is_oauth(self, tmp_path):
        """Auth-owned keys are replaced wholesale: a leftover ``pat`` would be resurrected by
        ``gather_auth`` despite ``auth_method: oauth``."""
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "pat", "pat": "secret-pat"},
            set_default=True,
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "oauth", "client_id": "CLI", "scope": "api:read"},
            set_default=True,
        )
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert "pat" not in env
        assert env["auth_method"] == "oauth"
        assert env["scope"] == "api:read"

    def test_drops_stale_password_when_re_login_is_oauth(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {},
                    "PROD": {
                        "base_url": "https://example.com",
                        "login": "someone",
                        "password": "x" * 32,
                    },
                }
            )
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "oauth", "client_id": "CLI"},
            set_default=False,
        )
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert "login" not in env
        assert "password" not in env

    def test_validates_the_merged_result_and_leaves_file_untouched(self, tmp_path):
        """Validation runs on the merge, not just on *env_data*: a broken key kept by the merge is
        caught before any write, so the config on disk survives intact."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(
            yaml.dump({"GENERAL": {}, "PROD": {"base_url": "https://example.com", "engine": "bogus"}})
        )
        before = config_path.read_text()
        with pytest.raises(ValidationError):
            write_environment_to_config(
                config_path,
                "PROD",
                {"base_url": "https://example.com", "auth_method": "oauth", "client_id": "CLI"},
                set_default=False,
            )
        assert config_path.read_text() == before

    def test_set_default_false(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"}, set_default=True)
        write_environment_to_config(config_path, "TEST", {"base_url": "https://test.example.com"}, set_default=False)
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert "TEST" in data

    def test_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "sub" / "dir" / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"}, set_default=True)
        assert config_path.is_file()


class TestRoundTrip:
    """The writer's output must parse back through the reader (``ConfigFile``)."""

    def test_pat_env_round_trips(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "login": OAUTH_LOGIN, "password": "secret-pat"},
            set_default=True,
        )
        config_file = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        env = config_file.environments["PROD"]
        assert env.auth is not None
        assert env.auth.login == OAUTH_LOGIN
        assert env.auth.password.get_secret_value() == "secret-pat"
        assert env.config.base_url == "https://example.com/"

    def test_oauth_env_round_trips(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "oauth", "client_id": "cid"},
            set_default=True,
        )
        config_file = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        env = config_file.environments["PROD"]
        assert env.auth is None
        assert env.auth_method == "oauth"
        assert env.client_id == "cid"
        assert env.config.base_url == "https://example.com/"

    def test_rejects_unparseable_env(self, tmp_path):
        # base_url is required by BfabricClientConfig; without it the written file would fail to
        # load on the next connect(). The writer must reject it up front rather than persist a
        # broken environment.
        config_path = tmp_path / "config.yml"
        with pytest.raises((ValueError, TypeError)):
            write_environment_to_config(
                config_path, "PROD", {"login": OAUTH_LOGIN, "password": "secret-pat"}, set_default=True
            )

    def test_does_not_corrupt_existing_file_on_invalid_env(self, tmp_path):
        # A rejected write must leave any pre-existing config untouched.
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "GOOD", {"base_url": "https://good.example.com"}, set_default=True)
        before = config_path.read_text()
        with pytest.raises((ValueError, TypeError)):
            write_environment_to_config(
                config_path, "BAD", {"login": OAUTH_LOGIN, "password": "secret-pat"}, set_default=True
            )
        assert config_path.read_text() == before

    @pytest.mark.parametrize("reserved", ["default", "GENERAL"])
    def test_rejects_reserved_env_name(self, tmp_path, reserved):
        # The reader reserves "default" (explicit validator) and consumes "GENERAL" as the general
        # section, so an environment under either name would never load back.
        config_path = tmp_path / "config.yml"
        with pytest.raises(ValueError):
            write_environment_to_config(config_path, reserved, {"base_url": "https://example.com"}, set_default=True)
        assert not config_path.exists()


class TestSetDefaultConfig:
    @staticmethod
    def _write_two_env_config(config_path):
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {"base_url": "https://prod.example.com"},
                    "TEST": {"base_url": "https://test.example.com"},
                }
            )
        )

    def test_sets_default_to_existing_env(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path)
        set_default_config(config_path, "TEST")
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "TEST"

    def test_preserves_other_environments(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path)
        set_default_config(config_path, "TEST")
        data = yaml.safe_load(config_path.read_text())
        assert data["PROD"]["base_url"] == "https://prod.example.com"
        assert data["TEST"]["base_url"] == "https://test.example.com"

    def test_raises_on_unknown_env_and_leaves_file_unchanged(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path)
        before = config_path.read_text()
        with pytest.raises(ValueError):
            set_default_config(config_path, "NOPE")
        assert config_path.read_text() == before

    def test_raises_on_missing_file(self, tmp_path):
        config_path = tmp_path / "nonexistent.yml"
        with pytest.raises(FileNotFoundError):
            set_default_config(config_path, "PROD")

    def test_tightens_permissions(self, tmp_path):
        # Switching the default must not loosen an already-strict file, and should tighten a
        # pre-existing group/world-readable one (a config may hold a PAT in another environment).
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path)
        config_path.chmod(0o644)
        set_default_config(config_path, "TEST")
        mode = stat.S_IMODE(os.stat(config_path).st_mode)
        assert mode == 0o600


class TestRemoveEnvironmentFromConfig:
    @staticmethod
    def _write_two_env_config(config_path, default="PROD"):
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": default},
                    "PROD": {"base_url": "https://prod.example.com"},
                    "TEST": {"base_url": "https://test.example.com"},
                }
            )
        )

    def test_removes_env_and_preserves_others(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path, default="PROD")
        remove_environment_from_config(config_path, "TEST")
        data = yaml.safe_load(config_path.read_text())
        assert "TEST" not in data
        assert data["PROD"]["base_url"] == "https://prod.example.com"
        # Removing a non-default env leaves the default untouched.
        assert data["GENERAL"]["default_config"] == "PROD"

    def test_removing_default_env_clears_default(self, tmp_path):
        # A dangling default_config would make ConfigFile refuse to load the file, so removing the
        # environment that is the default must also clear the default.
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path, default="PROD")
        remove_environment_from_config(config_path, "PROD")
        data = yaml.safe_load(config_path.read_text())
        assert "PROD" not in data
        assert data.get("GENERAL", {}).get("default_config") is None
        # The result must still parse back through the reader.
        config_file = ConfigFile.model_validate(data)
        assert set(config_file.environments) == {"TEST"}

    def test_raises_on_unknown_env_and_leaves_file_unchanged(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path)
        before = config_path.read_text()
        with pytest.raises(ValueError):
            remove_environment_from_config(config_path, "NOPE")
        assert config_path.read_text() == before

    def test_raises_on_missing_file(self, tmp_path):
        config_path = tmp_path / "nonexistent.yml"
        with pytest.raises(FileNotFoundError):
            remove_environment_from_config(config_path, "PROD")

    def test_tightens_permissions(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path)
        config_path.chmod(0o644)
        remove_environment_from_config(config_path, "TEST")
        mode = stat.S_IMODE(os.stat(config_path).st_mode)
        assert mode == 0o600


class TestClearEnvironmentCredentials:
    """Credential-only removal: the environment stays configured and usable for a fresh login."""

    def test_strips_pat_and_keeps_the_environment(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "pat", "pat": "secret-pat"},
            set_default=True,
        )
        removed = clear_environment_credentials(config_path, "PROD")
        assert removed == ("pat",)
        data = yaml.safe_load(config_path.read_text())
        assert "pat" not in data["PROD"]
        assert data["PROD"]["base_url"] == "https://example.com"
        assert data["GENERAL"]["default_config"] == "PROD"

    def test_strips_login_and_password(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "login": "someone", "password": "x" * 32},
            set_default=True,
        )
        removed = clear_environment_credentials(config_path, "PROD")
        assert set(removed) == {"login", "password"}
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert "login" not in env
        assert "password" not in env

    def test_keeps_the_oauth_login_recipe(self, tmp_path):
        """OAuth secrets live in the token cache, so the env keeps everything a re-login needs."""
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {
                "base_url": "https://example.com",
                "auth_method": "oauth",
                "client_id": "CLI",
                "scope": "api:write tus",
            },
            set_default=True,
        )
        assert clear_environment_credentials(config_path, "PROD") == ()
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert env["base_url"] == "https://example.com"
        assert env["client_id"] == "CLI"
        assert env["scope"] == "api:write tus"

    def test_result_still_parses_back(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "pat", "pat": "secret-pat"},
            set_default=True,
        )
        _ = clear_environment_credentials(config_path, "PROD")
        config_file = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        assert config_file.environments["PROD"].auth is None

    def test_leaves_other_environments_alone(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com", "auth_method": "pat", "pat": "p"}, set_default=True
        )
        write_environment_to_config(
            config_path,
            "TEST",
            {"base_url": "https://test.example.com", "auth_method": "pat", "pat": "t"},
            set_default=False,
        )
        _ = clear_environment_credentials(config_path, "PROD")
        data = yaml.safe_load(config_path.read_text())
        assert data["TEST"]["pat"] == "t"

    def test_raises_on_unknown_env_and_leaves_file_unchanged(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"}, set_default=True)
        before = config_path.read_text()
        with pytest.raises(ValueError):
            clear_environment_credentials(config_path, "NOPE")
        assert config_path.read_text() == before

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            clear_environment_credentials(tmp_path / "nonexistent.yml", "PROD")

    def test_tightens_permissions(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com", "auth_method": "pat", "pat": "p"}, set_default=True
        )
        config_path.chmod(0o644)
        _ = clear_environment_credentials(config_path, "PROD")
        assert stat.S_IMODE(os.stat(config_path).st_mode) == 0o600


class TestClientCredentialsSecretOwnership:
    """``client_secret`` is auth-owned: replaced on re-login, and cleared as an inline secret."""

    def test_switching_auth_method_drops_stale_client_secret(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {
                "base_url": "https://example.com",
                "auth_method": "client_credentials",
                "client_id": "cron",
                "client_secret": "s3cret",
            },
            set_default=True,
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com", "auth_method": "pat", "pat": "tok"},
            set_default=False,
        )
        data = yaml.safe_load(config_path.read_text())
        assert "client_secret" not in data["PROD"]

    def test_clear_credentials_removes_client_secret(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {
                "base_url": "https://example.com",
                "auth_method": "client_credentials",
                "client_id": "cron",
                "client_secret": "s3cret",
            },
            set_default=True,
        )
        removed = clear_environment_credentials(config_path, "PROD")
        assert "client_secret" in removed
        assert "client_secret" not in yaml.safe_load(config_path.read_text())["PROD"]
