from __future__ import annotations

from bfabric import Bfabric, BfabricClientConfig
from bfabric.config import BfabricAuth
from bfabric.config.config_data import ConfigData
from pydantic import SecretStr
from starlette.authentication import BaseUser

from bfabric_asgi_auth.session_data import SessionData


class BfabricUser(BaseUser):
    """Authenticated bfabric user, set on scope["user"] by BfabricAuthMiddleware."""

    _session_data: SessionData

    def __init__(self, session_data: SessionData) -> None:
        self._session_data = session_data

    @property
    def is_authenticated(self) -> bool:  # pyright: ignore[reportImplicitOverride]
        return True

    @property
    def display_name(self) -> str:  # pyright: ignore[reportImplicitOverride]
        return self._session_data.bfabric_auth_login

    @property
    def identity(self) -> str:  # pyright: ignore[reportImplicitOverride]
        return f"{self._session_data.bfabric_instance}:{self._session_data.bfabric_auth_login}"

    @property
    def session_data(self) -> SessionData:
        return self._session_data

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
