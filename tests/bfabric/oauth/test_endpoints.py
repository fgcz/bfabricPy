from __future__ import annotations

import pytest

from bfabric.config.base_url import BaseUrl
from bfabric.oauth import authorize_url, token_url


class TestAuthorizeUrl:
    def test_appends_path(self):
        assert authorize_url(BaseUrl("https://example.com/bfabric")) == (
            "https://example.com/bfabric/rest/oauth/authorize"
        )

    def test_accepts_plain_str(self):
        assert authorize_url("https://example.com/bfabric") == "https://example.com/bfabric/rest/oauth/authorize"


class TestTokenUrl:
    def test_appends_path(self):
        assert token_url(BaseUrl("https://example.com/bfabric")) == "https://example.com/bfabric/rest/oauth/token"

    def test_accepts_plain_str(self):
        assert token_url("https://example.com/bfabric") == "https://example.com/bfabric/rest/oauth/token"


class TestNormalisation:
    @pytest.mark.parametrize("builder", [authorize_url, token_url])
    def test_trailing_slash_does_not_double_up(self, builder):
        # BaseUrl rstrips, so a trailing slash never reaches the f-string as a second separator.
        assert "//rest" not in builder(BaseUrl("https://example.com/bfabric/"))

    @pytest.mark.parametrize("builder", [authorize_url, token_url])
    def test_rejects_a_non_bfabric_url(self, builder):
        with pytest.raises(ValueError):
            builder("https://example.com/notbfabric")
