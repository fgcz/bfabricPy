from __future__ import annotations

import yaml

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
        assert data["PROD"]["auth_method"] == "pat"
        assert data["PROD"]["pat"] == "my-pat-token"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
        # Old-client-safety contract: never inline a (non-32-char) secret under `password`,
        # and never pair a `login` with it — else an unmodified <=1.19.0 client fails to
        # parse the whole file.
        assert "login" not in data["PROD"]
        assert "password" not in data["PROD"]
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

    def test_prompts_when_pat_omitted(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        mocker.patch("bfabric_scripts.cli.login.pat.getpass.getpass", return_value="prompted-token")
        cmd_login_pat(
            base_url="https://example.com/bfabric",
            config_env="PROD",
            config_file=config_file,
        )
        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["pat"] == "prompted-token"

    def test_cancel_at_set_default_aborts(self, tmp_path, mocker, capsys):
        config_file = tmp_path / "config.yml"
        getpass = mocker.patch("bfabric_scripts.cli.login.pat.getpass.getpass")
        # No --set-default given: the user reaches the confirm prompt and cancels it (Ctrl-C -> None).
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=None)
        cmd_login_pat(
            base_url="https://example.com/bfabric",
            pat="tok",
            config_env="PROD",
            config_file=config_file,
        )
        # Cancelling aborts before any secret prompt and writes no config.
        getpass.assert_not_called()
        assert not config_file.exists()
        assert "Login aborted." in capsys.readouterr().err

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
        assert data["PROD"]["auth_method"] == "pat"
