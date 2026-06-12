"""Configuration models for webapp OAuth 2.0 integrations."""

from __future__ import annotations

from pydantic import BaseModel, SecretStr

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE


class OAuthClientCredentials(BaseModel):
    """OAuth client credentials for a registered webapp."""

    client_id: str
    client_secret: SecretStr
    scope: str = DEFAULT_OAUTH_SCOPE


class WebappOAuthSettings(BaseModel):
    """Full OAuth settings for a B-Fabric webapp integration."""

    base_url: str
    credentials: OAuthClientCredentials
