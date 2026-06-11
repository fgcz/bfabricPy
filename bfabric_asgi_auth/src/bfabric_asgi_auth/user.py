from __future__ import annotations

from typing import TYPE_CHECKING, override

from bfabric import Bfabric, BfabricClientConfig
from bfabric.config import BfabricAuth
from bfabric.config.config_data import ConfigData
from pydantic import SecretStr
from starlette.authentication import BaseUser

from bfabric_asgi_auth.session_data import SessionData

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from bfabric_asgi_auth.oauth_session_data import OAuthSessionData


class BfabricUser(BaseUser):
    """Authenticated bfabric user, set on scope["user"] by BfabricAuthMiddleware."""

    _session_data: SessionData

    def __init__(self, session_data: SessionData) -> None:
        self._session_data = session_data

    @property
    @override
    def is_authenticated(self) -> bool:
        return True

    @property
    @override
    def display_name(self) -> str:
        return self.login

    @property
    @override
    def identity(self) -> str:
        return f"{self.login}@{self.instance}"

    @property
    def login(self) -> str:
        return self._session_data.bfabric_auth_login

    @property
    def instance(self) -> str:
        return self._session_data.bfabric_instance

    @property
    def entity_class(self) -> str:
        return self._session_data.entity_class

    @property
    def entity_id(self) -> int:
        return self._session_data.entity_id

    @property
    def job_id(self) -> int:
        return self._session_data.job_id

    @property
    def application_id(self) -> int:
        return self._session_data.application_id

    def get_bfabric_client(self) -> Bfabric:
        """Create a Bfabric client authenticated as this user."""
        config = ConfigData(
            client=BfabricClientConfig.model_validate({"base_url": self._session_data.bfabric_instance}),
            auth=BfabricAuth(
                login=self._session_data.bfabric_auth_login,
                password=SecretStr(self._session_data.bfabric_auth_password),
            ),
        )
        return Bfabric(config)


class BfabricOAuthUser(BaseUser):
    """Authenticated B-Fabric user via OAuth 2.0 (JWT/refresh-token path).

    The user client is rebuilt on each call to :meth:`get_bfabric_client` from the
    stored refresh token.  A ``live_session`` reference allows the refresh callback to
    write an updated token back to the Starlette session cookie before response-start.
    """

    _session_data: OAuthSessionData
    _live_session: MutableMapping[str, object]
    _client_id: str
    _client_secret: str

    def __init__(
        self,
        session_data: OAuthSessionData,
        live_session: MutableMapping[str, object],
        *,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._session_data = session_data
        self._live_session = live_session
        self._client_id = client_id
        self._client_secret = client_secret

    # --- BaseUser interface ---

    @property
    @override
    def is_authenticated(self) -> bool:
        return True

    @property
    @override
    def display_name(self) -> str:
        return self.subject or ""

    @property
    @override
    def identity(self) -> str:
        return f"{self.subject}@{self._session_data.base_url}"

    # --- B-Fabric entity context (from JWT claims) ---

    @property
    def subject(self) -> str | None:
        return self._session_data.context.subject

    @property
    def entity_id(self) -> int | None:
        return self._session_data.context.entity_id

    @property
    def entity_class(self) -> str | None:
        return self._session_data.context.entity_class_name

    @property
    def application_id(self) -> int | None:
        return self._session_data.context.application_id

    @property
    def job_id(self) -> int | None:
        return self._session_data.context.job_id

    # --- Client builder ---

    def get_bfabric_client(self) -> Bfabric:
        """Return a :class:`Bfabric` client for the authenticated user.

        Builds a new client from the stored refresh token on each call.  When the
        token is refreshed, :meth:`_on_token_refresh` writes the new token back to
        the live session dict so it is persisted to the cookie before response-start.
        """
        return Bfabric.connect_oauth_token(
            self._session_data.base_url,
            self._session_data.token,
            client_id=self._client_id,
            client_secret=self._client_secret,
            token_cache_path=None,
            on_token_refresh=self._on_token_refresh,
        )

    def _on_token_refresh(self, new_token: dict[str, object]) -> None:
        """Write the refreshed token back to the live Starlette session dict."""
        self._live_session["token"] = dict(new_token)
