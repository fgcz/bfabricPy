"""Tests for create_oauth_validator."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from bfabric.experimental.webapp_oauth_settings import OAuthClientCredentials, WebappOAuthSettings
from bfabric_asgi_auth.token_validation.oauth_strategy import create_oauth_validator
from bfabric_asgi_auth.token_validation.strategy import OAuthExchangeSuccess, TokenValidationError


@pytest.fixture
def settings() -> WebappOAuthSettings:
    return WebappOAuthSettings(
        base_url="https://bfabric.example.com/bfabric/",
        credentials=OAuthClientCredentials(
            client_id="app-id",
            client_secret="app-secret",  # type: ignore[arg-type]
        ),
    )


class TestCreateOAuthValidator:
    async def test_successful_exchange_returns_oauth_exchange_success(self, mocker, settings):
        from bfabric._oauth.url_token import UrlTokenContext

        context = UrlTokenContext(subject="alice", entity_id=7)
        token = {"access_token": "at", "refresh_token": "rt"}
        mocker.patch(
            "bfabric_asgi_auth.token_validation.oauth_strategy.exchange_launch_token",
            return_value=(token, context),
        )

        validator = create_oauth_validator(settings)
        result = await validator(SecretStr("launch.jwt.token"))

        assert isinstance(result, OAuthExchangeSuccess)
        assert result.base_url == "https://bfabric.example.com/bfabric"
        assert result.token == token
        assert result.context.subject == "alice"

    async def test_strips_trailing_slash_from_base_url(self, mocker, settings):
        from bfabric._oauth.url_token import UrlTokenContext

        context = UrlTokenContext(subject="alice")
        mocker.patch(
            "bfabric_asgi_auth.token_validation.oauth_strategy.exchange_launch_token",
            return_value=({"access_token": "at"}, context),
        )
        validator = create_oauth_validator(settings)
        result = await validator(SecretStr("jwt"))

        assert isinstance(result, OAuthExchangeSuccess)
        assert not result.base_url.endswith("/")

    async def test_exchange_failure_returns_error(self, mocker, settings):
        mocker.patch(
            "bfabric_asgi_auth.token_validation.oauth_strategy.exchange_launch_token",
            side_effect=Exception("network error"),
        )

        validator = create_oauth_validator(settings)
        result = await validator(SecretStr("bad.jwt"))

        assert isinstance(result, TokenValidationError)
        assert "network error" in result.error

    async def test_forwards_credentials_to_exchange(self, mocker, settings):
        from bfabric._oauth.url_token import UrlTokenContext

        mock_exchange = mocker.patch(
            "bfabric_asgi_auth.token_validation.oauth_strategy.exchange_launch_token",
            return_value=({"access_token": "at"}, UrlTokenContext()),
        )
        validator = create_oauth_validator(settings)
        await validator(SecretStr("my.launch.jwt"))

        mock_exchange.assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            "my.launch.jwt",
            client_id="app-id",
            client_secret="app-secret",
        )
