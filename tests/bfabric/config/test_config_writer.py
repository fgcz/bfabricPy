from __future__ import annotations

import os
import stat

import pytest
import yaml

from bfabric.config.config_writer import write_environment_to_config


class TestWriteEnvironmentToConfig:
    def test_creates_new_file(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"})
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert data["PROD"]["base_url"] == "https://example.com"

    def test_sets_permissions(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"})
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
        write_environment_to_config(config_path, "PROD", {"login": "__oauth__", "password": "secret-pat"})
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
        write_environment_to_config(config_path, "NEW", {"base_url": "https://new.example.com"})
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "NEW"
        assert data["OLD"]["base_url"] == "https://old.example.com"
        assert data["NEW"]["base_url"] == "https://new.example.com"

    def test_overwrites_existing_env(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://v1.example.com"})
        write_environment_to_config(config_path, "PROD", {"base_url": "https://v2.example.com"})
        data = yaml.safe_load(config_path.read_text())
        assert data["PROD"]["base_url"] == "https://v2.example.com"

    def test_set_default_false(self, tmp_path):
        config_path = tmp_path / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"})
        write_environment_to_config(config_path, "TEST", {"base_url": "https://test.example.com"}, set_default=False)
        data = yaml.safe_load(config_path.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert "TEST" in data

    def test_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "sub" / "dir" / "config.yml"
        write_environment_to_config(config_path, "PROD", {"base_url": "https://example.com"})
        assert config_path.is_file()
