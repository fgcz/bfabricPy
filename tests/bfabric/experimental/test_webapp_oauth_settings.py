from __future__ import annotations

from pydantic import SecretStr

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric.experimental.webapp_oauth_settings import OAuthClientCredentials, WebappOAuthSettings


def test_oauth_client_credentials_defaults():
    creds = OAuthClientCredentials(client_id="cid", client_secret="shh")  # pyright: ignore[reportArgumentType]
    assert isinstance(creds.client_secret, SecretStr)
    assert creds.client_secret.get_secret_value() == "shh"
    assert creds.scope == DEFAULT_OAUTH_SCOPE


def test_webapp_oauth_settings():
    settings = WebappOAuthSettings(
        base_url="https://example.com/bfabric",
        credentials=OAuthClientCredentials(
            client_id="cid",
            client_secret="shh",  # pyright: ignore[reportArgumentType]
            scope="api:read",
        ),
    )
    assert settings.base_url == "https://example.com/bfabric"
    assert settings.credentials.client_id == "cid"
    assert settings.credentials.scope == "api:read"
