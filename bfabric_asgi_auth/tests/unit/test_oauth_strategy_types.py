"""Tests for OAuthExchangeSuccess strategy type."""

from __future__ import annotations

from bfabric._oauth.url_token import UrlTokenContext
from bfabric_asgi_auth.token_validation.strategy import OAuthExchangeSuccess, TokenValidationError


class TestOAuthExchangeSuccess:
    def test_has_success_true(self):
        context = UrlTokenContext(subject="alice")
        result = OAuthExchangeSuccess(
            base_url="https://example.com/bfabric",
            token={"access_token": "at", "refresh_token": "rt"},
            context=context,
        )
        assert result.success is True

    def test_stores_base_url(self):
        context = UrlTokenContext(subject="alice")
        result = OAuthExchangeSuccess(
            base_url="https://example.com/bfabric",
            token={"access_token": "at"},
            context=context,
        )
        assert result.base_url == "https://example.com/bfabric"

    def test_stores_token_and_context(self):
        context = UrlTokenContext(subject="alice", entity_id=7)
        token = {"access_token": "at", "refresh_token": "rt"}
        result = OAuthExchangeSuccess(base_url="https://example.com/bfabric", token=token, context=context)
        assert result.token == token
        assert result.context.subject == context.subject
        assert result.context.entity_id == context.entity_id

    def test_discriminator_distinguishes_from_error(self):
        """OAuthExchangeSuccess and TokenValidationError must not be confused by isinstance checks."""
        ok = OAuthExchangeSuccess(
            base_url="https://example.com",
            token={},
            context=UrlTokenContext(),
        )
        err = TokenValidationError(error="bad")
        assert ok.success is True
        assert err.success is False
