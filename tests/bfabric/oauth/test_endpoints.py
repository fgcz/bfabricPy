from __future__ import annotations

import pytest

from bfabric.config.base_url import BaseUrl
from bfabric.oauth import https_base_url, token_url
from bfabric.oauth._endpoints import authorize_url


class TestTokenUrl:
    def test_appends_path(self):
        assert token_url(BaseUrl("https://example.com/bfabric")) == "https://example.com/bfabric/rest/oauth/token"

    def test_accepts_plain_str(self):
        assert token_url("https://example.com/bfabric") == "https://example.com/bfabric/rest/oauth/token"

    def test_validates_the_base_url(self):
        # Only that the validation happens -- what BaseUrl accepts is tested where BaseUrl lives.
        with pytest.raises(ValueError):
            token_url("https://example.com/notbfabric")


class TestHttpsBaseUrl:
    def test_upgrades_http(self):
        assert https_base_url("http://fgcz-bfabric.uzh.ch/bfabric") == "https://fgcz-bfabric.uzh.ch/bfabric"

    def test_keeps_the_port(self):
        assert https_base_url("http://example.com:8080/bfabric") == "https://example.com:8080/bfabric"

    def test_leaves_https_alone(self):
        assert https_base_url("https://example.com/bfabric") == "https://example.com/bfabric"

    @pytest.mark.parametrize(
        "url", ["http://localhost:8080/bfabric", "http://127.0.0.1:8000/bfabric", "http://[::1]:8000/bfabric"]
    )
    def test_leaves_loopback_alone_for_local_development(self, url):
        assert https_base_url(url) == url

    def test_token_url_uses_https(self):
        assert token_url("http://example.com/bfabric") == "https://example.com/bfabric/rest/oauth/token"

    def test_authorize_url_uses_https(self):
        url = authorize_url(
            "http://example.com/bfabric",
            client_id="c",
            redirect_uri="http://127.0.0.1:1/callback",
            code_challenge="x",
            state="s",
            scope="api:read",
        )
        assert url.startswith("https://example.com/bfabric/rest/oauth/authorize?")
