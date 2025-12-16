from __future__ import annotations

from typing import Self

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bfabric import BfabricAuth


class BfabricTokenValidationSettings(BaseModel):
    validation_bfabric_instance: str
    supported_bfabric_instances: list[str]
    feeder_user_credentials: dict[str, BfabricAuth]

    @model_validator(mode="after")
    def _valid_validation_instance(self) -> Self:
        if self.validation_bfabric_instance not in self.supported_bfabric_instances:
            raise ValueError("validation_bfabric_instance must be one of supported_bfabric_instances")
        return self

    @model_validator(mode="after")
    def _valid_feeder_user_credentials(self) -> Self:
        if any(key not in self.supported_bfabric_instances for key in self.feeder_user_credentials):
            raise ValueError("feeder_user_credentials must contain only supported bfabric instances.")
        return self


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
