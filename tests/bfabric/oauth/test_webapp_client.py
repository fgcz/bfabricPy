"""Tests for WebappClient.create after the A4 refactor.

WebappClient.create now delegates to:
  - exchange_launch_token (bfabric.experimental.webapp_oauth) for steps 1+2
  - Bfabric.connect_oauth_token for step 3 (user client)
  - Bfabric.connect_oauth (unchanged) for step 4 (service client)
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bfabric._oauth.url_token import UrlTokenContext
from bfabric._oauth.webapp_client import WebappClient
from bfabric.bfabric import Bfabric

_PATCH_EXCHANGE_LAUNCH = "bfabric.experimental.webapp_oauth.exchange_launch_token"
_PATCH_CONNECT_OAUTH_TOKEN = "bfabric.bfabric.Bfabric.connect_oauth_token"
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
def mock_context() -> UrlTokenContext:
    return UrlTokenContext.model_validate(SAMPLE_CLAIMS)


@pytest.fixture
def mock_service_client(mocker):
    return mocker.MagicMock(name="service_client")


class TestWebappClientCreate:
    def test_returns_correct_user_service_context(self, mocker, mock_token_dict, mock_context, mock_service_client):
        mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context))
        mock_user_client = mocker.MagicMock(name="user_client")
        mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=mock_user_client)
        mocker.patch(_PATCH_CONNECT_OAUTH, return_value=mock_service_client)
        mocker.patch(_PATCH_LOG)

        wc = WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="short.lived.jwt",
            client_id="app-id",
            client_secret="app-secret",
        )

        assert wc.service is mock_service_client
        assert wc.user is mock_user_client
        assert wc.context is mock_context
        assert wc.context.entity_id == 123
        assert wc.context.subject == "jdoe"

    def test_forwards_parameters_to_exchange_launch_token(self, mocker, mock_token_dict, mock_context):
        mock_exchange = mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context))
        mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=mocker.MagicMock())
        mocker.patch(_PATCH_CONNECT_OAUTH, return_value=mocker.MagicMock())
        mocker.patch(_PATCH_LOG)

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

    def test_forwards_token_and_credentials_to_connect_oauth_token(self, mocker, mock_token_dict, mock_context):
        mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context))
        mock_connect_token = mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=mocker.MagicMock())
        mocker.patch(_PATCH_CONNECT_OAUTH, return_value=mocker.MagicMock())
        mocker.patch(_PATCH_LOG)

        WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
            user_token_cache_path="/tmp/user_cache",
        )

        mock_connect_token.assert_called_once_with(
            "https://bfabric.example.com/bfabric",
            mock_token_dict,
            client_id="cid",
            client_secret="csecret",
            token_cache_path="/tmp/user_cache",
        )

    def test_forwards_parameters_to_connect_oauth(self, mocker, mock_token_dict, mock_context):
        mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context))
        mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=mocker.MagicMock())
        mock_connect_oauth = mocker.patch(_PATCH_CONNECT_OAUTH, return_value=mocker.MagicMock())
        mocker.patch(_PATCH_LOG)

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

    def test_default_scope(self, mocker, mock_token_dict, mock_context):
        mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context))
        mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=mocker.MagicMock())
        mock_connect_oauth = mocker.patch(_PATCH_CONNECT_OAUTH, return_value=mocker.MagicMock())
        mocker.patch(_PATCH_LOG)

        WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
        )

        assert mock_connect_oauth.call_args.kwargs["scope"] == "api:read api:write"


class TestWebappClientFrozen:
    @pytest.fixture
    def mock_user_client(self, mocker):
        return mocker.MagicMock(name="user_client")

    @pytest.fixture
    def mock_service_client(self, mocker):
        return mocker.MagicMock(name="service_client")

    @pytest.fixture
    def mock_context(self) -> UrlTokenContext:
        return UrlTokenContext(entity_id=1, subject="u")

    def test_cannot_reassign_user(self, mock_user_client, mock_service_client, mock_context, mocker):
        wc = WebappClient(user=mock_user_client, service=mock_service_client, context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.user = mocker.MagicMock()  # type: ignore[misc]

    def test_cannot_reassign_service(self, mock_user_client, mock_service_client, mock_context, mocker):
        wc = WebappClient(user=mock_user_client, service=mock_service_client, context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.service = mocker.MagicMock()  # type: ignore[misc]

    def test_cannot_reassign_context(self, mock_user_client, mock_service_client, mock_context, mocker):
        wc = WebappClient(user=mock_user_client, service=mock_service_client, context=mock_context)
        with pytest.raises(FrozenInstanceError):
            wc.context = mocker.MagicMock()  # type: ignore[misc]


class TestWebappClientIndependence:
    def test_user_and_service_are_independent(self, mocker):
        mock_token_dict = {"access_token": "at", "refresh_token": "rt", "token_type": "Bearer"}
        mock_context = UrlTokenContext.model_validate({"sub": "u"})
        mocker.patch(_PATCH_EXCHANGE_LAUNCH, return_value=(mock_token_dict, mock_context))
        mock_user = mocker.MagicMock(name="user")
        mocker.patch(_PATCH_CONNECT_OAUTH_TOKEN, return_value=mock_user)
        mocker.patch(_PATCH_CONNECT_OAUTH, return_value=mocker.MagicMock(name="service"))
        mocker.patch(_PATCH_LOG)

        wc = WebappClient.create(
            base_url="https://bfabric.example.com/bfabric",
            launch_token="jwt",
            client_id="cid",
            client_secret="csecret",
        )

        assert wc.user is not wc.service
