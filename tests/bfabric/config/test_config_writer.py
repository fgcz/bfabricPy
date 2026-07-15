from __future__ import annotations

import os
import stat

import pytest
import yaml

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_file import ConfigFile
from bfabric.config.config_writer import set_default_config, write_environment_to_config


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

    def test_overwrites_existing_env(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://v1.example.com"}, set_default=True)
        write_environment_to_config(config_path, "PROD", {"base_url": "https://v2.example.com"}, set_default=True)
        data = yaml.safe_load(config_path.read_text())
        assert data["PROD"]["base_url"] == "https://v2.example.com"

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
