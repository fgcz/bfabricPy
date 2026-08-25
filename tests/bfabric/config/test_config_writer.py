from __future__ import annotations

import os
import stat

import pytest
import yaml
from pydantic import ValidationError

from bfabric.config import BaseUrl
from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_file import ConfigFile
from bfabric.config.config_writer import (
    clear_environment_credentials,
    read_environment_auth_keys,
    remove_environment_from_config,
    set_default_config,
    write_environment_to_config,
)


class TestWriteEnvironmentToConfig:
    def test_writes_a_str_subclass_as_a_plain_scalar(self, tmp_path):
        """A ``BaseUrl`` needs no coercion by the caller, and must not reach the file as an
        unloadable ``!!python/object/new:`` tag."""
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": BaseUrl("https://example.com/bfabric")},
            auth="replace",
            set_default=True,
        )
        assert "!!python/object" not in config_path.read_text()
        assert yaml.safe_load(config_path.read_text())["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_creates_new_file(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
        )
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_sets_permissions(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
        )
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
            {"base_url": "https://example.com/bfabric", "login": "__oauth__", "password": "secret-pat"},
            auth="replace",
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
                    "OLD": {"base_url": "https://old.example.com/bfabric"},
                }
            )
        )
        write_environment_to_config(
            config_path, "NEW", {"base_url": "https://new.example.com/bfabric"}, auth="replace", set_default=True
        )
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "NEW"
        assert data["OLD"]["base_url"] == "https://old.example.com/bfabric"
        assert data["NEW"]["base_url"] == "https://new.example.com/bfabric"

    def test_overwrites_supplied_keys_of_existing_env(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://v1.example.com/bfabric"}, auth="replace", set_default=True
        )
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://v2.example.com/bfabric"}, auth="replace", set_default=True
        )
        data = yaml.safe_load(config_path.read_text())
        assert data["PROD"]["base_url"] == "https://v2.example.com/bfabric"

    def test_preserves_unrelated_keys_of_existing_env(self, tmp_path):
        """A re-login must not wipe hand-written keys the CLI knows nothing about."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {
                        "base_url": "https://v1.example.com/bfabric",
                        "application_ids": {"app": 123},
                        "job_notification_emails": "me@example.com",
                    },
                }
            )
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://v2.example.com/bfabric", "auth_method": "oauth", "client_id": "CLI"},
            auth="replace",
            set_default=True,
        )
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert env["application_ids"] == {"app": 123}
        assert env["job_notification_emails"] == "me@example.com"
        assert env["base_url"] == "https://v2.example.com/bfabric"

    def test_drops_stale_pat_when_re_login_is_oauth(self, tmp_path):
        """Auth-owned keys are replaced wholesale: a leftover ``pat`` would be resurrected by
        ``gather_auth`` despite ``auth_method: oauth``."""
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "secret-pat"},
            auth="replace",
            set_default=True,
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "oauth", "client_id": "CLI", "scope": "api:read"},
            auth="replace",
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
                        "base_url": "https://example.com/bfabric",
                        "login": "someone",
                        "password": "x" * 32,
                    },
                }
            )
        )
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "oauth", "client_id": "CLI"},
            auth="replace",
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
            yaml.dump({"GENERAL": {}, "PROD": {"base_url": "https://example.com/bfabric", "engine": "bogus"}})
        )
        before = config_path.read_text()
        with pytest.raises(ValidationError):
            write_environment_to_config(
                config_path,
                "PROD",
                {"base_url": "https://example.com/bfabric", "auth_method": "oauth", "client_id": "CLI"},
                auth="replace",
                set_default=False,
            )
        assert config_path.read_text() == before

    def test_set_default_false(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
        )
        write_environment_to_config(
            config_path, "TEST", {"base_url": "https://test.example.com/bfabric"}, auth="replace", set_default=False
        )
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert "TEST" in data

    def test_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "sub" / "dir" / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
        )
        assert config_path.is_file()


class TestRoundTrip:
    """The writer's output must parse back through the reader (``ConfigFile``)."""

    def test_pat_env_round_trips(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "login": OAUTH_LOGIN, "password": "secret-pat"},
            auth="replace",
            set_default=True,
        )
        config_file = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        env = config_file.environments["PROD"]
        assert env.auth is not None
        assert env.auth.login == OAUTH_LOGIN
        assert env.auth.password.get_secret_value() == "secret-pat"
        assert env.config.base_url == "https://example.com/bfabric"

    def test_oauth_env_round_trips(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "oauth", "client_id": "cid"},
            auth="replace",
            set_default=True,
        )
        config_file = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        env = config_file.environments["PROD"]
        assert env.auth is None
        assert env.auth_method == "oauth"
        assert env.client_id == "cid"
        assert env.config.base_url == "https://example.com/bfabric"

    def test_rejects_unparseable_env(self, tmp_path):
        # base_url is required by BfabricClientConfig; without it the written file would fail to
        # load on the next connect(). The writer must reject it up front rather than persist a
        # broken environment.
        config_path = tmp_path / "config.yml"
        with pytest.raises((ValueError, TypeError)):
            write_environment_to_config(
                config_path, "PROD", {"login": OAUTH_LOGIN, "password": "secret-pat"}, auth="replace", set_default=True
            )

    def test_does_not_corrupt_existing_file_on_invalid_env(self, tmp_path):
        # A rejected write must leave any pre-existing config untouched.
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "GOOD", {"base_url": "https://good.example.com/bfabric"}, auth="replace", set_default=True
        )
        before = config_path.read_text()
        with pytest.raises((ValueError, TypeError)):
            write_environment_to_config(
                config_path, "BAD", {"login": OAUTH_LOGIN, "password": "secret-pat"}, auth="replace", set_default=True
            )
        assert config_path.read_text() == before

    @pytest.mark.parametrize("reserved", ["default", "GENERAL"])
    def test_rejects_reserved_env_name(self, tmp_path, reserved):
        # The reader reserves "default" (explicit validator) and consumes "GENERAL" as the general
        # section, so an environment under either name would never load back.
        config_path = tmp_path / "config.yml"
        with pytest.raises(ValueError):
            write_environment_to_config(
                config_path, reserved, {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
            )
        assert not config_path.exists()


class TestSetDefaultConfig:
    @staticmethod
    def _write_two_env_config(config_path):
        config_path.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "PROD"},
                    "PROD": {"base_url": "https://prod.example.com/bfabric"},
                    "TEST": {"base_url": "https://test.example.com/bfabric"},
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
        assert data["PROD"]["base_url"] == "https://prod.example.com/bfabric"
        assert data["TEST"]["base_url"] == "https://test.example.com/bfabric"

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
                    "PROD": {"base_url": "https://prod.example.com/bfabric"},
                    "TEST": {"base_url": "https://test.example.com/bfabric"},
                }
            )
        )

    def test_removes_env_and_preserves_others(self, tmp_path):
        config_path = tmp_path / "config.yml"
        self._write_two_env_config(config_path, default="PROD")
        remove_environment_from_config(config_path, "TEST")
        data = yaml.safe_load(config_path.read_text())
        assert "TEST" not in data
        assert data["PROD"]["base_url"] == "https://prod.example.com/bfabric"
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
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "secret-pat"},
            auth="replace",
            set_default=True,
        )
        removed = clear_environment_credentials(config_path, "PROD")
        assert removed == ("pat",)
        data = yaml.safe_load(config_path.read_text())
        assert "pat" not in data["PROD"]
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
        assert data["GENERAL"]["default_config"] == "PROD"

    def test_strips_login_and_password(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "login": "someone", "password": "x" * 32},
            auth="replace",
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
                "base_url": "https://example.com/bfabric",
                "auth_method": "oauth",
                "client_id": "CLI",
                "scope": "api:write tus",
            },
            auth="replace",
            set_default=True,
        )
        assert clear_environment_credentials(config_path, "PROD") == ()
        env = yaml.safe_load(config_path.read_text())["PROD"]
        assert env["base_url"] == "https://example.com/bfabric"
        assert env["client_id"] == "CLI"
        assert env["scope"] == "api:write tus"

    def test_result_still_parses_back(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "secret-pat"},
            auth="replace",
            set_default=True,
        )
        _ = clear_environment_credentials(config_path, "PROD")
        config_file = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        assert config_file.environments["PROD"].auth is None

    def test_leaves_other_environments_alone(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "p"},
            auth="replace",
            set_default=True,
        )
        write_environment_to_config(
            config_path,
            "TEST",
            {"base_url": "https://test.example.com/bfabric", "auth_method": "pat", "pat": "t"},
            auth="replace",
            set_default=False,
        )
        _ = clear_environment_credentials(config_path, "PROD")
        data = yaml.safe_load(config_path.read_text())
        assert data["TEST"]["pat"] == "t"

    def test_raises_on_unknown_env_and_leaves_file_unchanged(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(
            config_path, "PROD", {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
        )
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
            config_path,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "p"},
            auth="replace",
            set_default=True,
        )
        config_path.chmod(0o644)
        _ = clear_environment_credentials(config_path, "PROD")
        assert stat.S_IMODE(os.stat(config_path).st_mode) == 0o600


class TestAuthMode:
    """The two modes corrupt in opposite directions, so the caller must say which it means."""

    def _write_oauth_env(self, config_file):
        write_environment_to_config(
            config_file,
            "PROD",
            {
                "base_url": "https://example.com/bfabric",
                "auth_method": "oauth",
                "client_id": "CLI",
                "scope": "api:read",
            },
            auth="replace",
            set_default=True,
        )

    def test_mode_is_required(self, tmp_path):
        with pytest.raises(TypeError):
            write_environment_to_config(  # pyright: ignore[reportCallIssue]
                tmp_path / "config.yml",
                "PROD",
                {"base_url": "https://example.com/bfabric"},
                set_default=True,
            )

    def test_replace_drops_unmentioned_auth_keys(self, tmp_path):
        config_file = tmp_path / "config.yml"
        self._write_oauth_env(config_file)
        write_environment_to_config(
            config_file,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "token"},
            auth="replace",
            set_default=False,
        )
        env = yaml.safe_load(config_file.read_text())["PROD"]
        assert env["auth_method"] == "pat"
        assert "client_id" not in env
        assert "scope" not in env

    def test_merge_keeps_unmentioned_auth_keys(self, tmp_path):
        config_file = tmp_path / "config.yml"
        self._write_oauth_env(config_file)
        write_environment_to_config(
            config_file,
            "PROD",
            {"client_id": "other-client"},
            auth="merge",
            set_default=False,
        )
        env = yaml.safe_load(config_file.read_text())["PROD"]
        assert env["client_id"] == "other-client"
        assert env["scope"] == "api:read"
        assert env["auth_method"] == "oauth"

    def test_merge_deletes_keys_set_to_none(self, tmp_path):
        config_file = tmp_path / "config.yml"
        self._write_oauth_env(config_file)
        write_environment_to_config(config_file, "PROD", {"scope": None}, auth="merge", set_default=False)
        env = yaml.safe_load(config_file.read_text())["PROD"]
        assert "scope" not in env
        assert env["client_id"] == "CLI"

    def test_non_auth_keys_survive_both_modes(self, tmp_path):
        config_file = tmp_path / "config.yml"
        write_environment_to_config(
            config_file,
            "PROD",
            {"base_url": "https://example.com/bfabric", "application_ids": {"app": 1}},
            auth="replace",
            set_default=True,
        )
        write_environment_to_config(
            config_file,
            "PROD",
            {"auth_method": "pat", "pat": "token"},
            auth="merge",
            set_default=False,
        )
        env = yaml.safe_load(config_file.read_text())["PROD"]
        assert env["application_ids"] == {"app": 1}
        assert env["base_url"] == "https://example.com/bfabric"


class TestReadEnvironmentAuthKeys:
    def test_missing_file(self, tmp_path):
        assert read_environment_auth_keys(tmp_path / "nope.yml", "PROD") == {}

    def test_missing_environment(self, tmp_path):
        config_file = tmp_path / "config.yml"
        write_environment_to_config(
            config_file, "PROD", {"base_url": "https://example.com/bfabric"}, auth="replace", set_default=True
        )
        assert read_environment_auth_keys(config_file, "OTHER") == {}

    def test_returns_only_auth_keys(self, tmp_path):
        config_file = tmp_path / "config.yml"
        write_environment_to_config(
            config_file,
            "PROD",
            {
                "base_url": "https://example.com/bfabric",
                "application_ids": {"app": 1},
                "auth_method": "oauth",
                "client_id": "CLI",
            },
            auth="replace",
            set_default=True,
        )
        assert read_environment_auth_keys(config_file, "PROD") == {"auth_method": "oauth", "client_id": "CLI"}


class TestValidateWritableEnvironment:
    @pytest.mark.parametrize(
        ("env_data", "match"),
        [
            ({"auth_method": "client_credentials", "client_id": "svc"}, "client_secret"),
            ({"auth_method": "pat"}, "pat"),
            ({"auth_method": "pat", "pat": "t", "client_secret": "s"}, "client_secret"),
            ({"auth_method": "oauth", "client_id": "CLI", "pat": "t"}, "pat"),
            ({"auth_method": "oauth", "client_id": "CLI", "client_secret": "s"}, "client_secret"),
            ({"auth_method": "password"}, "login"),
            ({"registration_access_token": "tok"}, "registration"),
            ({"registration_client_uri": "https://x.test"}, "registration"),
        ],
    )
    def test_rejects_incoherent_combination(self, tmp_path, env_data, match):
        config_file = tmp_path / "config.yml"
        with pytest.raises(ValueError, match=match):
            write_environment_to_config(
                config_file,
                "PROD",
                {"base_url": "https://example.com/bfabric"} | env_data,
                auth="replace",
                set_default=True,
            )
        assert not config_file.exists()

    @pytest.mark.parametrize(
        "env_data",
        [
            {"auth_method": "oauth", "client_id": "CLI", "scope": "api:read"},
            {"auth_method": "pat", "pat": "token"},
            {"auth_method": "client_credentials", "client_id": "svc", "client_secret": "s"},
            {"auth_method": "password", "login": "user", "password": "p" * 32},
            {"login": "user", "password": "p" * 32},
            {"scope": "api:read"},
            {"registration_access_token": "tok", "registration_client_uri": "https://x.test/reg"},
        ],
        ids=["oauth", "pat", "svcacct", "password", "legacy", "scope-only", "registration-pair"],
    )
    def test_accepts_coherent_combination(self, tmp_path, env_data):
        config_file = tmp_path / "config.yml"
        write_environment_to_config(
            config_file,
            "PROD",
            {"base_url": "https://example.com/bfabric"} | env_data,
            auth="replace",
            set_default=True,
        )
        assert yaml.safe_load(config_file.read_text())["PROD"]


class TestAtomicWrite:
    """The config file holds the user's only credentials, so a partial write must not be possible."""

    def _write(self, config_file, **kwargs):
        write_environment_to_config(
            config_file,
            "PROD",
            {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "token"},
            auth="replace",
            **kwargs,
        )

    def test_leaves_no_temp_file_behind(self, tmp_path):
        config_file = tmp_path / "config.yml"
        self._write(config_file, set_default=True)
        assert [path.name for path in tmp_path.iterdir()] == ["config.yml"]

    def test_no_temp_file_left_when_serialization_fails(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        self._write(config_file, set_default=True)
        mocker.patch("bfabric.config.config_writer.yaml.dump", side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            self._write(config_file, set_default=False)

        assert [path.name for path in tmp_path.iterdir()] == ["config.yml"]
        assert yaml.safe_load(config_file.read_text())["PROD"]["pat"] == "token"

    def test_a_failed_write_leaves_the_previous_config_intact(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        self._write(config_file, set_default=True)
        before = config_file.read_text()

        real_write = os.write

        def partial_then_fail(fd, data):
            _ = real_write(fd, data[:20])
            raise OSError("disk full")

        mocker.patch("bfabric.config.config_writer.os.write", side_effect=partial_then_fail)
        with pytest.raises(OSError, match="disk full"):
            write_environment_to_config(
                config_file,
                "PROD",
                {"base_url": "https://example.com/bfabric", "auth_method": "pat", "pat": "rotated"},
                auth="replace",
                set_default=False,
            )

        assert config_file.read_text() == before
        assert [path.name for path in tmp_path.iterdir()] == ["config.yml"]

    def test_mode_is_600_for_a_new_file(self, tmp_path):
        config_file = tmp_path / "config.yml"
        self._write(config_file, set_default=True)
        assert stat.S_IMODE(config_file.stat().st_mode) == 0o600

    def test_mode_is_tightened_on_an_existing_loose_file(self, tmp_path):
        config_file = tmp_path / "config.yml"
        self._write(config_file, set_default=True)
        config_file.chmod(0o644)
        self._write(config_file, set_default=False)
        assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
