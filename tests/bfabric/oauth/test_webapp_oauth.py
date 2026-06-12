"""Tests for bfabric.experimental.webapp_oauth public module."""

from __future__ import annotations

import pytest

from bfabric._oauth.url_token import UrlTokenContext
from bfabric._oauth.webapp_client import WebappClient
from bfabric.experimental.webapp_oauth import DEFAULT_OAUTH_SCOPE, exchange_launch_token

_PATCH_EXCHANGE = "bfabric.experimental.webapp_oauth.exchange_token"
_PATCH_VERIFY_JWT = "bfabric.experimental.webapp_oauth.verify_jwt"

SAMPLE_CLAIMS = {
    "entityId": 7,
    "entityClassName": "Workunit",
    "applicationId": 3,
    "jobId": 99,
    "sub": "alice",
    "exp": 9999999999,
}


@pytest.fixture
def mock_token_dict() -> dict[str, object]:
    return {"access_token": "at123", "refresh_token": "rt456", "token_type": "Bearer"}


class TestExchangeLaunchToken:
    def test_returns_token_dict_and_context(self, mocker, mock_token_dict):
        mocker.patch(_PATCH_EXCHANGE, return_value=mock_token_dict)
        mocker.patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS))

        token_dict, context = exchange_launch_token(
            "https://bfabric.example.com/bfabric",
            "launch.jwt",
            client_id="cid",
            client_secret="csecret",
        )

        assert token_dict is mock_token_dict
        assert isinstance(context, UrlTokenContext)
        assert context.subject == "alice"
        assert context.entity_id == 7

    def test_forwards_args_to_exchange_token(self, mocker, mock_token_dict):
        mock_exchange = mocker.patch(_PATCH_EXCHANGE, return_value=mock_token_dict)
        mocker.patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS))

        exchange_launch_token(
            "https://bfabric.example.com/bfabric/",
            "my.jwt",
            client_id="app-id",
            client_secret="app-secret",
        )

        mock_exchange.assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            "my.jwt",
            client_id="app-id",
            client_secret="app-secret",
        )

    def test_verifies_access_token_jwt(self, mocker, mock_token_dict):
        mocker.patch(_PATCH_EXCHANGE, return_value=mock_token_dict)
        mock_verify = mocker.patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS))

        exchange_launch_token(
            "https://bfabric.example.com/bfabric",
            "jwt",
            client_id="cid",
            client_secret="secret",
        )

        mock_verify.assert_called_once_with("https://bfabric.example.com/bfabric", "at123")

    def test_strips_trailing_slash(self, mocker, mock_token_dict):
        mock_exchange = mocker.patch(_PATCH_EXCHANGE, return_value=mock_token_dict)
        mocker.patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS))

        exchange_launch_token(
            "https://bfabric.example.com/bfabric/",
            "jwt",
            client_id="cid",
            client_secret="secret",
        )

        assert mock_exchange.call_args[0][0] == "https://bfabric.example.com/bfabric"


class TestPublicReExports:
    def test_default_oauth_scope_exported(self):
        assert isinstance(DEFAULT_OAUTH_SCOPE, str)
        assert DEFAULT_OAUTH_SCOPE  # non-empty

    def test_url_token_context_exported(self):
        assert UrlTokenContext is not None

    def test_webapp_client_exported(self):
        assert WebappClient is not None
