from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bfabric._oauth.registration import register_client, register_webapp


@pytest.fixture
def mock_httpx_post():
    with patch("bfabric._oauth.registration.httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "client_id": "new-client-id",
            "client_secret": "new-client-secret",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        yield mock_post


_TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"


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
                "grant_types": [_TOKEN_EXCHANGE, "refresh_token"],
                "scope": "api:read api:write",
            },
            headers={"Authorization": "Bearer bearer-token"},
            timeout=30,
        )
        assert result["client_id"] == "new-client-id"
        assert result["client_secret"] == "new-client-secret"

    def test_with_service_user_adds_client_credentials_grant(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
            service_user="gfeeder",
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["service_user_login"] == "gfeeder"
        assert call_body["grant_types"] == [_TOKEN_EXCHANGE, "refresh_token", "client_credentials"]

    def test_without_service_user_no_client_credentials_grant(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["grant_types"] == [_TOKEN_EXCHANGE, "refresh_token"]
        assert "service_user_login" not in call_body

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

    def test_explicit_grant_types_override(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
            grant_types=["authorization_code", "refresh_token"],
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["grant_types"] == ["authorization_code", "refresh_token"]

    def test_without_optional_params(self, mock_httpx_post):
        register_client(
            base_url="https://example.com/bfabric",
            token="tok",
            client_name="app",
            redirect_uri="http://localhost/cb",
        )

        call_body = mock_httpx_post.call_args[1]["json"]
        assert "service_user_login" not in call_body
        assert call_body["scope"] == "api:read api:write"

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
        with patch("bfabric._oauth.registration.httpx.post") as mock_post:
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


_PATCH_REGISTER_CLIENT = "bfabric._oauth.registration.register_client"


class TestRegisterWebapp:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock(name="bfabric_client")
        client.config.base_url = "https://example.com/bfabric/"
        client.save.return_value = MagicMock(name="save_result")
        return client

    @pytest.fixture
    def mock_register(self):
        with patch(_PATCH_REGISTER_CLIENT) as mock_rc:
            mock_rc.return_value = {
                "id": 258,
                "client_id": "new-cid",
                "client_secret": "new-csecret",
            }
            yield mock_rc

    def test_calls_register_client_and_saves_application(self, mock_client, mock_register):
        result = register_webapp(
            client=mock_client,
            token="bearer-tok",
            app_name="My Webapp",
            web_url="https://myapp.example.com/",
        )

        mock_register.assert_called_once_with(
            base_url="https://example.com/bfabric",
            token="bearer-tok",
            client_name="My Webapp",
            redirect_uri="https://myapp.example.com/",
            service_user=None,
            scope="api:read api:write",
        )
        mock_client.save.assert_called_once_with(
            "application",
            {
                "name": "My Webapp",
                "weburl": "https://myapp.example.com/",
                "oauthclientid": 258,
                "type": "WebApp",
            },
        )
        assert result["oauth"] == mock_register.return_value
        assert result["application"] == mock_client.save.return_value

    def test_forwards_service_user(self, mock_client, mock_register):
        register_webapp(
            client=mock_client,
            token="tok",
            app_name="app",
            web_url="https://app.example.com/",
            service_user="svc",
        )

        assert mock_register.call_args[1]["service_user"] == "svc"

    def test_forwards_scope(self, mock_client, mock_register):
        register_webapp(
            client=mock_client,
            token="tok",
            app_name="app",
            web_url="https://app.example.com/",
            scope="api:read",
        )

        assert mock_register.call_args[1]["scope"] == "api:read"

    def test_updates_existing_application(self, mock_client, mock_register):
        register_webapp(
            client=mock_client,
            token="tok",
            app_name="app",
            web_url="https://app.example.com/",
            application_id=42,
        )

        save_obj = mock_client.save.call_args[0][1]
        assert save_obj["id"] == 42

    def test_sets_optional_fields(self, mock_client, mock_register):
        register_webapp(
            client=mock_client,
            token="tok",
            app_name="app",
            web_url="https://app.example.com/",
            technology_id=7,
            description="A test app",
        )

        save_obj = mock_client.save.call_args[0][1]
        assert save_obj["technologyid"] == 7
        assert save_obj["description"] == "A test app"

    def test_omits_optional_fields_when_not_provided(self, mock_client, mock_register):
        register_webapp(
            client=mock_client,
            token="tok",
            app_name="app",
            web_url="https://app.example.com/",
        )

        save_obj = mock_client.save.call_args[0][1]
        assert "id" not in save_obj
        assert "technologyid" not in save_obj
        assert "description" not in save_obj