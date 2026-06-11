"""Unit tests for BfabricOAuthUser."""

from __future__ import annotations

import datetime
from collections.abc import MutableMapping

import pytest
from bfabric import Bfabric

from bfabric._oauth.url_token import UrlTokenContext
from bfabric_asgi_auth.oauth_session_data import OAuthSessionData
from bfabric_asgi_auth.user import BfabricOAuthUser


@pytest.fixture
def sample_context() -> UrlTokenContext:
    return UrlTokenContext(
        entity_id=42,
        entity_class_name="Workunit",
        application_id=7,
        job_id=99,
        subject="jdoe",
        expires_at=datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc),
    )


@pytest.fixture
def sample_token() -> dict[str, object]:
    return {"access_token": "at", "refresh_token": "rt", "expires_at": 9999999999}


@pytest.fixture
def session_data(sample_token, sample_context) -> OAuthSessionData:
    return OAuthSessionData(
        base_url="https://bfabric.example.com/bfabric",
        token=sample_token,
        context=sample_context,
    )


@pytest.fixture
def live_session(session_data) -> dict[str, object]:
    return dict(session_data.model_dump(mode="json"))


@pytest.fixture
def user(session_data, live_session) -> BfabricOAuthUser:
    return BfabricOAuthUser(
        session_data=session_data,
        live_session=live_session,
        client_id="app-id",
        client_secret="app-secret",
    )


class TestBfabricOAuthUserProperties:
    def test_is_authenticated(self, user):
        assert user.is_authenticated is True

    def test_subject_from_context(self, user):
        assert user.subject == "jdoe"

    def test_display_name_is_subject(self, user):
        assert user.display_name == "jdoe"

    def test_identity(self, user):
        assert user.identity == "jdoe@https://bfabric.example.com/bfabric"

    def test_entity_id_from_context(self, user):
        assert user.entity_id == 42

    def test_entity_class_from_context(self, user):
        assert user.entity_class == "Workunit"

    def test_application_id_from_context(self, user):
        assert user.application_id == 7

    def test_job_id_from_context(self, user):
        assert user.job_id == 99


class TestBfabricOAuthUserClient:
    def test_get_bfabric_client_calls_connect_oauth_token(self, mocker, session_data, live_session):
        mock_connect = mocker.patch.object(Bfabric, "connect_oauth_token", return_value=mocker.MagicMock())
        user = BfabricOAuthUser(
            session_data=session_data,
            live_session=live_session,
            client_id="app-id",
            client_secret="app-secret",
        )

        user.get_bfabric_client()

        mock_connect.assert_called_once()
        call_kwargs = mock_connect.call_args
        assert call_kwargs[0][0] == "https://bfabric.example.com/bfabric"
        assert call_kwargs[0][1] == session_data.token
        assert call_kwargs[1]["client_id"] == "app-id"
        assert call_kwargs[1]["client_secret"] == "app-secret"
        assert call_kwargs[1]["token_cache_path"] is None
        assert callable(call_kwargs[1]["on_token_refresh"])

    def test_token_refresh_writes_back_to_live_session(self, mocker, session_data, live_session):
        """When a token refresh fires, the live session dict is updated in place."""
        captured_callback: list[object] = []

        def fake_connect(base_url, token, *, client_id, client_secret, token_cache_path, on_token_refresh):
            captured_callback.append(on_token_refresh)
            return mocker.MagicMock()

        mocker.patch.object(Bfabric, "connect_oauth_token", side_effect=fake_connect)
        user = BfabricOAuthUser(
            session_data=session_data,
            live_session=live_session,
            client_id="app-id",
            client_secret="app-secret",
        )
        user.get_bfabric_client()

        # Simulate a token refresh
        new_token = {"access_token": "new_at", "refresh_token": "new_rt", "expires_at": 9999999999}
        callback = captured_callback[0]
        callback(new_token)  # type: ignore[operator]

        # The live_session dict should be updated
        assert live_session["token"] == new_token
