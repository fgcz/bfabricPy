from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch

import pytest

from bfabric._oauth.url_token import UrlTokenContext
from bfabric._oauth.webapp_client import WebappClient

_PATCH_FROM_URL_TOKEN = "bfabric.bfabric.Bfabric.from_url_token"
_PATCH_CONNECT_OAUTH = "bfabric.bfabric.Bfabric.connect_oauth"


@pytest.fixture
def mock_context() -> UrlTokenContext:
    return UrlTokenContext(
        entity_id=123,
        entity_class_name="Workunit",
        application_id=456,
        job_id=789,
        client_id="my-client",
        subject="jdoe",
        expires_at=None,
    )


@pytest.fixture
def mock_user_client() -> MagicMock:
    return MagicMock(name="user_client")


@pytest.fixture
def mock_service_client() -> MagicMock:
    return MagicMock(name="service_client")


class TestWebappClientCreate:
    def test_returns_correct_user_service_context(
        self, mock_user_client, mock_service_client, mock_context
    ):
        with (
            patch(
                _PATCH_FROM_URL_TOKEN,
                return_value=(mock_user_client, mock_context),
            ),
            patch(
                _PATCH_CONNECT_OAUTH,
                return_value=mock_service_client,
            ),
        ):
            wc = WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                jwt="some.jwt.token",
                refresh_token="some-refresh-token",
                client_id="app-id",
                client_secret="app-secret",
            )

        assert wc.user is mock_user_client
        assert wc.service is mock_service_client
        assert wc.context is mock_context

    def test_forwards_parameters_to_from_url_token(self, mock_service_client, mock_context):
        mock_user = MagicMock(name="user_client")
        with (
            patch(
                _PATCH_FROM_URL_TOKEN,
                return_value=(mock_user, mock_context),
            ) as mock_from_url_token,
            patch(
                _PATCH_CONNECT_OAUTH,
                return_value=mock_service_client,
            ),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                jwt="my.jwt",
                refresh_token="my-rt",
                client_id="cid",
                client_secret="csecret",
                user_token_cache_path="/tmp/user_cache",
            )

        mock_from_url_token.assert_called_once_with(
            base_url="https://bfabric.example.com/bfabric",
            jwt="my.jwt",
            refresh_token="my-rt",
            token_cache_path="/tmp/user_cache",
        )

    def test_forwards_parameters_to_connect_oauth(self, mock_context):
        mock_user = MagicMock(name="user_client")
        mock_service = MagicMock(name="service_client")
        with (
            patch(
                _PATCH_FROM_URL_TOKEN,
                return_value=(mock_user, mock_context),
            ),
            patch(
                _PATCH_CONNECT_OAUTH,
                return_value=mock_service,
            ) as mock_connect_oauth,
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                jwt="jwt",
                client_id="cid",
                client_secret="csecret",
                scope="api:read",
                service_token_cache_path="/tmp/svc_cache",
            )

        mock_connect_oauth.assert_called_once_with(
            client_id="cid",
            client_secret="csecret",
            base_url="https://bfabric.example.com/bfabric",
            scope="api:read",
            token_cache_path="/tmp/svc_cache",
        )

    def test_default_scope(self, mock_context):
        mock_user = MagicMock(name="user_client")
        mock_service = MagicMock(name="service_client")
        with (
            patch(
                _PATCH_FROM_URL_TOKEN,
                return_value=(mock_user, mock_context),
            ),
            patch(
                _PATCH_CONNECT_OAUTH,
                return_value=mock_service,
            ) as mock_connect_oauth,
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                jwt="jwt",
                client_id="cid",
                client_secret="csecret",
            )

        assert mock_connect_oauth.call_args.kwargs["scope"] == "api:read api:write"

    def test_refresh_token_defaults_to_none(self, mock_context):
        mock_user = MagicMock(name="user_client")
        mock_service = MagicMock(name="service_client")
        with (
            patch(
                _PATCH_FROM_URL_TOKEN,
                return_value=(mock_user, mock_context),
            ) as mock_from_url_token,
            patch(
                _PATCH_CONNECT_OAUTH,
                return_value=mock_service,
            ),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                jwt="jwt",
                client_id="cid",
                client_secret="csecret",
            )

        assert mock_from_url_token.call_args.kwargs["refresh_token"] is None


class TestWebappClientFrozen:
    def test_cannot_reassign_user(self, mock_user_client, mock_service_client, mock_context):
        wc = WebappClient(user=mock_user_client, service=mock_service_client, context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.user = MagicMock()  # type: ignore[misc]

    def test_cannot_reassign_service(self, mock_user_client, mock_service_client, mock_context):
        wc = WebappClient(user=mock_user_client, service=mock_service_client, context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.service = MagicMock()  # type: ignore[misc]

    def test_cannot_reassign_context(self, mock_user_client, mock_service_client, mock_context):
        wc = WebappClient(user=mock_user_client, service=mock_service_client, context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.context = MagicMock()  # type: ignore[misc]


class TestWebappClientIndependence:
    def test_user_and_service_are_independent(self, mock_context):
        mock_user = MagicMock(name="user_client")
        mock_service = MagicMock(name="service_client")
        with (
            patch(
                _PATCH_FROM_URL_TOKEN,
                return_value=(mock_user, mock_context),
            ),
            patch(
                _PATCH_CONNECT_OAUTH,
                return_value=mock_service,
            ),
        ):
            wc = WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                jwt="jwt",
                client_id="cid",
                client_secret="csecret",
            )

        assert wc.user is not wc.service
