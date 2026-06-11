from __future__ import annotations

import pytest

from bfabric._oauth.token_exchange import exchange_token, introspect_token
from bfabric._oauth.url_token import UrlTokenContext

BASE_URL = "https://example.com/bfabric"


class TestExchangeToken:
    def test_posts_correct_payload(self, mocker):
        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_at",
            "refresh_token": "new_rt",
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        result = exchange_token(
            BASE_URL,
            "short_lived_jwt",
            client_id="app-id",
            client_secret="app-secret",
        )

        mock_post.assert_called_once_with(
            f"{BASE_URL}/rest/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token": "short_lived_jwt",
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            },
            auth=("app-id", "app-secret"),
            timeout=30,
        )
        mock_response.raise_for_status.assert_called_once()
        assert result == {
            "access_token": "new_at",
            "refresh_token": "new_rt",
            "token_type": "Bearer",
        }

    def test_strips_trailing_slash(self, mocker):
        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {"access_token": "at"}
        mock_post.return_value = mock_response

        exchange_token(
            f"{BASE_URL}///",
            "jwt",
            client_id="cid",
            client_secret="cs",
        )

        url = mock_post.call_args[0][0]
        assert url == f"{BASE_URL}/rest/oauth/token"

    def test_raises_on_http_error(self, mocker):
        import httpx

        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=mocker.MagicMock(), response=mocker.MagicMock()
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            exchange_token(BASE_URL, "jwt", client_id="cid", client_secret="cs")


class TestIntrospectToken:
    def test_posts_and_returns_context(self, mocker):
        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {
            "active": True,
            "entityId": 123,
            "entityClassName": "Workunit",
            "applicationId": 456,
            "jobId": 789,
            "sub": "jdoe",
            "client_id": "app-id",
        }
        mock_post.return_value = mock_response

        ctx = introspect_token(
            BASE_URL,
            "access_token_value",
            client_id="app-id",
            client_secret="app-secret",
        )

        mock_post.assert_called_once_with(
            f"{BASE_URL}/rest/oauth/introspect",
            data={"token": "access_token_value"},
            auth=("app-id", "app-secret"),
            timeout=30,
        )
        mock_response.raise_for_status.assert_called_once()
        assert isinstance(ctx, UrlTokenContext)
        assert ctx.entity_id == 123
        assert ctx.entity_class_name == "Workunit"
        assert ctx.application_id == 456
        assert ctx.job_id == 789
        assert ctx.subject == "jdoe"
        assert ctx.client_id == "app-id"

    def test_handles_minimal_claims(self, mocker):
        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {"active": True, "sub": "user"}
        mock_post.return_value = mock_response

        ctx = introspect_token(BASE_URL, "at", client_id="cid", client_secret="cs")

        assert ctx.entity_id is None
        assert ctx.application_id is None
        assert ctx.subject == "user"

    def test_strips_trailing_slash(self, mocker):
        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.json.return_value = {"sub": "u"}
        mock_post.return_value = mock_response

        introspect_token(f"{BASE_URL}///", "at", client_id="cid", client_secret="cs")

        url = mock_post.call_args[0][0]
        assert url == f"{BASE_URL}/rest/oauth/introspect"

    def test_raises_on_http_error(self, mocker):
        import httpx

        mock_post = mocker.patch("bfabric._oauth.token_exchange.httpx.post")
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=mocker.MagicMock(), response=mocker.MagicMock()
        )
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            introspect_token(BASE_URL, "at", client_id="cid", client_secret="cs")
