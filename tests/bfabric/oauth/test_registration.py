from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bfabric.oauth._registration import register_client


@pytest.fixture
def mock_httpx_post():
    with patch("bfabric.oauth._registration.httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "client_id": "new-client-id",
            "client_secret": "new-client-secret",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        yield mock_post


class TestRegisterClient:
    def test_basic_registration(self, mock_httpx_post):
        result = register_client(
            base_url="https://example.com/bfabric",
            token="bearer-token",
            client_name="my-app",
            redirect_uri="http://localhost:8050/callback",
        )

        mock_httpx_post.assert_called_once_with(
            "https://example.com/bfabric/rest/oauth/register",
            json={
                "client_name": "my-app",
                "redirect_uris": ["http://localhost:8050/callback"],
            },
            headers={"Authorization": "Bearer bearer-token"},
        )
        assert result["client_id"] == "new-client-id"
        assert result["client_secret"] == "new-client-secret"

    def test_with_service_user(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
            service_user="gfeeder",
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["service_user_login"] == "gfeeder"

    def test_with_scope(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
            scope="api:read api:write",
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["scope"] == "api:read api:write"

    def test_without_optional_params(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert "service_user_login" not in call_body
        assert "scope" not in call_body

    def test_normalizes_trailing_slash(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric/",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
        )

        url = mock_httpx_post.call_args[0][0]
        assert url == "https://example.com/bfabric/rest/oauth/register"

    def test_raises_on_http_error(self):
        with patch("bfabric.oauth._registration.httpx.post") as mock_post:
            import httpx

            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Forbidden", request=MagicMock(), response=MagicMock()
            )
            mock_post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                register_client(
                    base_url="https://example.com/bfabric",
                    token="bad-token",
                    client_name="app",
                    redirect_uri="http://localhost/cb",
                )
