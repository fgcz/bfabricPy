from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bfabric import BfabricAuth


class ServerSettings(BaseSettings):
    # NOTE: environment variables will take priority over dotenv variables
    model_config: SettingsConfigDict = SettingsConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file=".env", env_file_encoding="utf-8"
    )
    # specific to the proxy:
    default_bfabric_instance: str | None = None

    # general bfabric web app settings
    validation_bfabric_instance: str
    feeder_user_credentials: dict[str, BfabricAuth]
    supported_bfabric_instances: list[str]

    @model_validator(mode="after")
    def _only_supported_bfabric_instances(self) -> ServerSettings:
        if self.validation_bfabric_instance not in self.supported_bfabric_instances:
            raise ValueError("validation_bfabric_instance must be one of supported_bfabric_instances")
        if self.default_bfabric_instance not in self.supported_bfabric_instances:
            raise ValueError("default_bfabric_instance must be one of supported_bfabric_instances")
        if any(key not in self.supported_bfabric_instances for key in self.feeder_user_credentials):
            raise ValueError("feeder_user_credentials must contain only supported bfabric instances.")
        return self
