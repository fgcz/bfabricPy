from __future__ import annotations

import json

import pytest
import yaml

from bfabric._oauth.token_cache import compute_token_cache_path
from bfabric_scripts.cli.login.logout import cmd_login_logout


@pytest.fixture(autouse=True)
def _clear_config_env(monkeypatch):
    monkeypatch.delenv("BFABRICPY_CONFIG_ENV", raising=False)


class TestCmdLoginLogout:
    def test_clears_oauth_token_cache(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        base_url = "https://example.com/bfabric"
        client_id = "my-app"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": base_url,
                    "auth_method": "oauth",
                    "client_id": client_id,
                },
            })
        )
        cache_path = compute_token_cache_path(base_url, client_id, "PROD").expanduser()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"access_token": "tok"}))

        cmd_login_logout(config_file=config_file)
        output = capsys.readouterr().out
        assert "cleared" in output
        assert not cache_path.exists()

    def test_non_oauth_env(self, tmp_path, capsys):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            yaml.dump({
                "GENERAL": {"default_config": "PROD"},
                "PROD": {
                    "base_url": "https://example.com/bfabric",
                    "login": "user",
                    "password": "x" * 32,
                },
            })
        )
        cmd_login_logout(config_file=config_file)
        output = capsys.readouterr().out
        assert "does not use OAuth" in output
