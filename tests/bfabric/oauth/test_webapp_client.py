from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch

import pytest

from bfabric._oauth.url_token import UrlTokenContext
from bfabric._oauth.webapp_client import WebappClient

_PATCH_EXCHANGE = "bfabric._oauth.token_exchange.exchange_token"
_PATCH_VERIFY_JWT = "bfabric._oauth.url_token.verify_jwt"
_PATCH_PROVIDER = "bfabric._oauth.credential_provider.OAuthCredentialProvider"
_PATCH_CONNECT_OAUTH = "bfabric.bfabric.Bfabric.connect_oauth"
_PATCH_LOG = "bfabric.bfabric.Bfabric._log_version_message"

SAMPLE_CLAIMS = {
    "entityId": 123,
    "entityClassName": "Workunit",
    "applicationId": 456,
    "jobId": 789,
    "client_id": "my-client",
    "sub": "jdoe",
    "exp": 1999999999,
}


@pytest.fixture
def mock_token_dict() -> dict[str, object]:
    return {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "token_type": "Bearer",
    }


@pytest.fixture
def mock_service_client() -> MagicMock:
    return MagicMock(name="service_client")


class TestWebappClientCreate:
    def test_returns_correct_user_service_context(self, mock_token_dict, mock_service_client):
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict),
            patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS)),
            patch(_PATCH_PROVIDER) as mock_provider_cls,
            patch(_PATCH_CONNECT_OAUTH, return_value=mock_service_client),
            patch(_PATCH_LOG),
        ):
            wc = WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="short.lived.jwt",
                client_id="app-id",
                client_secret="app-secret",
            )

        assert wc.service is mock_service_client
        assert wc.context.entity_id == 123
        assert wc.context.subject == "jdoe"
        assert wc.user._credential_provider is mock_provider_cls.return_value

    def test_forwards_parameters_to_exchange_token(self, mock_token_dict):
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict) as mock_exchange,
            patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS)),
            patch(_PATCH_PROVIDER),
            patch(_PATCH_CONNECT_OAUTH, return_value=MagicMock()),
            patch(_PATCH_LOG),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="my.launch.jwt",
                client_id="cid",
                client_secret="csecret",
            )

        mock_exchange.assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            "my.launch.jwt",
            client_id="cid",
            client_secret="csecret",
        )

    def test_verifies_exchanged_access_token_jwt(self, mock_token_dict):
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict),
            patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS)) as mock_verify,
            patch(_PATCH_PROVIDER),
            patch(_PATCH_CONNECT_OAUTH, return_value=MagicMock()),
            patch(_PATCH_LOG),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="jwt",
                client_id="cid",
                client_secret="csecret",
            )

        mock_verify.assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            "new_access_token",
        )

    def test_creates_user_provider_with_refresh_token(self, mock_token_dict):
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict),
            patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS)),
            patch(_PATCH_PROVIDER) as mock_provider_cls,
            patch(_PATCH_CONNECT_OAUTH, return_value=MagicMock()),
            patch(_PATCH_LOG),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="jwt",
                client_id="cid",
                client_secret="csecret",
                user_token_cache_path="/tmp/user_cache",
            )

        mock_provider_cls.assert_called_once_with(
            client_id="cid",
            client_secret="csecret",
            token_url="https://bfabric.example.com/bfabric/rest/oauth/token",
            token=mock_token_dict,
            grant_type="refresh_token",
            token_cache_path="/tmp/user_cache",
        )

    def test_forwards_parameters_to_connect_oauth(self, mock_token_dict):
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict),
            patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS)),
            patch(_PATCH_PROVIDER),
            patch(_PATCH_CONNECT_OAUTH, return_value=MagicMock()) as mock_connect_oauth,
            patch(_PATCH_LOG),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="jwt",
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

    def test_default_scope(self, mock_token_dict):
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict),
            patch(_PATCH_VERIFY_JWT, return_value=dict(SAMPLE_CLAIMS)),
            patch(_PATCH_PROVIDER),
            patch(_PATCH_CONNECT_OAUTH, return_value=MagicMock()) as mock_connect_oauth,
            patch(_PATCH_LOG),
        ):
            WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="jwt",
                client_id="cid",
                client_secret="csecret",
            )

        assert mock_connect_oauth.call_args.kwargs["scope"] == "api:read api:write"


class TestWebappClientFrozen:
    @pytest.fixture
    def mock_user_client(self) -> MagicMock:
        return MagicMock(name="user_client")

    @pytest.fixture
    def mock_service_client(self) -> MagicMock:
        return MagicMock(name="service_client")

    @pytest.fixture
    def mock_context(self) -> UrlTokenContext:
        return UrlTokenContext(entity_id=1, subject="u")

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
    def test_user_and_service_are_independent(self):
        mock_token_dict = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        with (
            patch(_PATCH_EXCHANGE, return_value=mock_token_dict),
            patch(_PATCH_VERIFY_JWT, return_value={"sub": "u"}),
            patch(_PATCH_PROVIDER),
            patch(_PATCH_CONNECT_OAUTH, return_value=MagicMock(name="service")),
            patch(_PATCH_LOG),
        ):
            wc = WebappClient.create(
                base_url="https://bfabric.example.com/bfabric",
                launch_token="jwt",
                client_id="cid",
                client_secret="csecret",
            )

        assert wc.user is not wc.service