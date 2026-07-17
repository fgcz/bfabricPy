from __future__ import annotations

import yaml

from bfabric_scripts.cli.login.manage import cmd_auth_list


class TestCmdAuthList:
    def test_lists_environments_and_marks_default(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump(
                {
                    "GENERAL": {"default_config": "TEST"},
                    "PROD": {"base_url": "https://prod.example.com", "auth_method": "oauth"},
                    "TEST": {"base_url": "https://test.example.com", "auth_method": "pat", "pat": "tok"},
                }
            )
        )
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "PROD" in output
        assert "TEST" in output
        # The default is flagged and each row carries the host + auth method.
        assert "(default)" in output
        assert "prod.example.com" in output
        assert "oauth" in output
        assert "pat" in output

    def test_missing_config_file(self, tmp_path, capsys):
        config_file = tmp_path / "nonexistent.yml"
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "not found" in output

    def test_no_environments(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump({"GENERAL": {}}))
        cmd_auth_list(config_file=config_file)
        output = capsys.readouterr().out
        assert "No environments configured" in output
