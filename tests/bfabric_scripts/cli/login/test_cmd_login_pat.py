from __future__ import annotations

from unittest.mock import patch

import yaml

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric_scripts.cli.login.pat import cmd_login_pat


class TestCmdLoginPat:
    def test_writes_config_with_flag(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        cmd_login_pat(
            base_url="https://example.com/bfabric",
            pat="my-pat-token",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["GENERAL"]["default_config"] == "PROD"
        assert data["PROD"]["login"] == OAUTH_LOGIN
        assert data["PROD"]["password"] == "my-pat-token"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
        # Warning should be printed when passing via flag
        err = capsys.readouterr().err
        assert "insecure" in err

    def test_strips_trailing_slash(self, tmp_path):
        config_file = tmp_path / "config.yml"
        cmd_login_pat(
            base_url="https://example.com/bfabric/",
            pat="tok",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"

    def test_prompts_when_pat_omitted(self, tmp_path):
        config_file = tmp_path / "config.yml"
        with patch("bfabric_scripts.cli.login.pat.getpass.getpass", return_value="prompted-token"):
            cmd_login_pat(
                base_url="https://example.com/bfabric",
                config_env="PROD",
                config_file=config_file,
            )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["password"] == "prompted-token"

    def test_set_default_false_does_not_set_default(self, tmp_path):
        config_file = tmp_path / "config.yml"
        cmd_login_pat(
            base_url="https://example.com/bfabric",
            pat="tok",
            config_env="PROD",
            config_file=config_file,
            set_default=False,
        )
        data = yaml.safe_load(config_file.read_text())
        assert "default_config" not in data["GENERAL"]
        assert data["PROD"]["login"] == OAUTH_LOGIN
