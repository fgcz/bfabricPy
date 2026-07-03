from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric._oauth.url_token import UrlTokenContext
from bfabric._oauth.webapp_client import WebappClient

# WebappClient.create composes three building blocks; we mock those, not their internals.
_PATCH_EXCHANGE_LAUNCH = "bfabric._oauth.launch_token.exchange_launch_token"
_PATCH_CONNECT_OAUTH_TOKEN = "bfabric.bfabric.Bfabric.connect_oauth_token"
_PATCH_CONNECT_OAUTH = "bfabric.bfabric.Bfabric.connect_oauth"

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
def mock_context() -> UrlTokenContext:
    return UrlTokenContext.model_validate(SAMPLE_CLAIMS)


@pytest.fixture
def patched(mocker, mock_token_dict, mock_context):
    """Patch the three primitives WebappClient.create composes; return the mocks."""
    user_client = mocker.MagicMock(name="user_client")
    service_client = mocker.MagicMock(name="service_client")
    return {
        "exchange": mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context)),
        "connect_oauth_token": mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=user_client),
        "connect_oauth": mocker.patch(_PATCH_CONNECT_OAUTH, return_value=service_client),
        "user": user_client,
        "service": service_client,
    }


class TestWebappClientCreate:
    def test_returns_correct_user_service_context(self, patched, mock_context):
        wc = WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="short.lived.jwt",
            client_id="app-id",
            client_secret="app-secret",
        )

        assert wc.user is patched["user"]
        assert wc.service is patched["service"]
        assert wc.context is mock_context
        assert wc.context.entity_id == 123
        assert wc.context.subject == "jdoe"

    def test_forwards_parameters_to_exchange_launch_token(self, patched):
        WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="my.launch.jwt",
            client_id="cid",
            client_secret="csecret",
        )

        patched["exchange"].assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            "my.launch.jwt",
            client_id="cid",
            client_secret="csecret",
        )

    def test_builds_user_client_from_exchanged_token(self, patched, mock_token_dict):
        WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
            user_token_cache_path="/tmp/user_cache",
        )

        patched["connect_oauth_token"].assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            mock_token_dict,
            client_id="cid",
            client_secret="csecret",
            token_cache_path="/tmp/user_cache",
        )

    def test_forwards_parameters_to_connect_oauth(self, patched):
        WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
            scope="api:read",
            service_token_cache_path="/tmp/svc_cache",
        )

        patched["connect_oauth"].assert_called_once_with(
            client_id="cid",
            client_secret="csecret",
            base_url="https://bfabric.example.com/bfabric",
            scope="api:read",
            token_cache_path="/tmp/svc_cache",
        )

    def test_default_scope(self, patched):
        WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
        )

        assert patched["connect_oauth"].call_args.kwargs["scope"] == DEFAULT_OAUTH_SCOPE


class TestWebappClientFrozen:
    @pytest.fixture
    def mock_context(self) -> UrlTokenContext:
        return UrlTokenContext(entity_id=1, subject="u")

    def test_cannot_reassign_user(self, mock_context, mocker):
        wc = WebappClient(user=mocker.MagicMock(), service=mocker.MagicMock(), context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.user = mocker.MagicMock()  # type: ignore[misc]

    def test_cannot_reassign_service(self, mock_context, mocker):
        wc = WebappClient(user=mocker.MagicMock(), service=mocker.MagicMock(), context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.service = mocker.MagicMock()  # type: ignore[misc]

    def test_cannot_reassign_context(self, mock_context, mocker):
        wc = WebappClient(user=mocker.MagicMock(), service=mocker.MagicMock(), context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.context = mocker.MagicMock()  # type: ignore[misc]


class TestWebappClientIndependence:
    def test_user_and_service_are_independent(self, patched):
        wc = WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
        )

        assert wc.user is not wc.service
