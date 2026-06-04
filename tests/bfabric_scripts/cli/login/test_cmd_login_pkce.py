from __future__ import annotations

import json
import time
from unittest.mock import patch, MagicMock

import yaml

from bfabric_scripts.cli.login.pkce import cmd_login_pkce


class TestCmdLoginPkce:
    def test_writes_config_and_caches_token(self, tmp_path):
        config_file = tmp_path / "config.yml"
        token = {
            "access_token": "jwt123",
            "refresh_token": "rt456",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }

        mock_session = MagicMock()
        mock_session.token = None
        mock_session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}

        with (
            patch("bfabric_scripts.cli.login.pkce.pkce_login", return_value=token) as mock_pkce,
            patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=mock_session),
        ):
            cmd_login_pkce(
                base_url="https://example.com/bfabric",
                client_id="test-client",
                env_name="PROD",
                config_file=config_file,
            )
            mock_pkce.assert_called_once()

        data = yaml.safe_load(config_file.read_text())
        assert data["PROD"]["auth_method"] == "oauth"
        assert data["PROD"]["client_id"] == "test-client"
        assert data["PROD"]["base_url"] == "https://example.com/bfabric"
