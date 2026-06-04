from __future__ import annotations

import yaml

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric_scripts.cli.login.pat import cmd_login_pat


class TestCmdLoginPat:
    def test_writes_config(self, tmp_path):
        config_file = tmp_path / "config.yml"
        cmd_login_pat(
            base_url="https://example.com/bfabric",
            pat="my-pat-token",
            env_name="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert data["PROD"]["login"] == OAUTH_LOGIN
        assert data["PROD"]["password"] == "my-pat-token"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_strips_trailing_slash(self, tmp_path):
        config_file = tmp_path / "config.yml"
        cmd_login_pat(
            base_url="https://example.com/bfabric/",
            pat="tok",
            env_name="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
