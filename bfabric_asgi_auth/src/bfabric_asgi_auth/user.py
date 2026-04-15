from __future__ import annotations

from typing import override

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
