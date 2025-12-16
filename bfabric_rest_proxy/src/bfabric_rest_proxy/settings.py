from __future__ import annotations

from bfabric.experimental.webapp_integration_settings import BfabricTokenValidationSettings
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings, BfabricTokenValidationSettings):  # pyright: ignore[reportUnsafeMultipleInheritance]
    # NOTE: environment variables will take priority over dotenv variables
    model_config: SettingsConfigDict = SettingsConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    # specific to the proxy:
    default_bfabric_instance: str | None = None

    @model_validator(mode="after")
    def _valid_default_instance(self) -> ServerSettings:
        if self.default_bfabric_instance not in self.supported_bfabric_instances:
            raise ValueError("default_bfabric_instance must be one of supported_bfabric_instances")
        return self
