from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from bfabric.config.base_url import BaseUrl
from bfabric.oauth import authorize_url, token_url


class TestAuthorizeUrl:
    @staticmethod
    def _build(**overrides) -> str:
        kwargs = {
            "client_id": "my-client",
            "redirect_uri": "https://app.example.com/callback",
            "code_challenge": "the-challenge",
            "state": "the-state",
            "scope": "api:read",
        }
        return authorize_url(overrides.pop("base_url", "https://example.com/bfabric"), **{**kwargs, **overrides})

    def test_targets_the_authorize_endpoint(self):
        assert self._build().startswith("https://example.com/bfabric/rest/oauth/authorize?")

    def test_carries_the_authorization_request_params(self):
        query = parse_qs(urlparse(self._build()).query)
        assert query == {
            "response_type": ["code"],
            "client_id": ["my-client"],
            "redirect_uri": ["https://app.example.com/callback"],
            "code_challenge": ["the-challenge"],
            "code_challenge_method": ["S256"],
            "state": ["the-state"],
            "scope": ["api:read"],
        }

    def test_percent_encodes_the_redirect_uri(self):
        # A raw "://" in the query would terminate the value at the first "&" a caller's URI carries.
        url = self._build(redirect_uri="https://app.example.com/cb?a=1&b=2")
        assert "https%3A%2F%2Fapp.example.com%2Fcb%3Fa%3D1%26b%3D2" in url
        assert parse_qs(urlparse(url).query)["redirect_uri"] == ["https://app.example.com/cb?a=1&b=2"]

    def test_accepts_a_base_url_instance(self):
        assert self._build(base_url=BaseUrl("https://example.com/bfabric")).startswith("https://example.com/bfabric/")


class TestTokenUrl:
    def test_appends_path(self):
        assert token_url(BaseUrl("https://example.com/bfabric")) == "https://example.com/bfabric/rest/oauth/token"

    def test_accepts_plain_str(self):
        assert token_url("https://example.com/bfabric") == "https://example.com/bfabric/rest/oauth/token"


def _builders():
    """Both endpoint builders, reduced to a one-argument form so the shared URL rules can be parametrised."""
    return [
        pytest.param(
            lambda base_url: authorize_url(
                base_url,
                client_id="c",
                redirect_uri="https://app.example.com/callback",
                code_challenge="ch",
                state="st",
                scope="api:read",
            ),
            id="authorize_url",
        ),
        pytest.param(token_url, id="token_url"),
    ]


class TestNormalisation:
    @pytest.mark.parametrize("builder", _builders())
    def test_trailing_slash_does_not_double_up(self, builder):
        # BaseUrl rstrips, so a trailing slash never reaches the f-string as a second separator.
        assert "//rest" not in builder(BaseUrl("https://example.com/bfabric/"))

    @pytest.mark.parametrize("builder", _builders())
    def test_rejects_a_non_bfabric_url(self, builder):
        with pytest.raises(ValueError):
            builder("https://example.com/notbfabric")
