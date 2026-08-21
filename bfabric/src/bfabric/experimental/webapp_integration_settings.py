from __future__ import annotations

from typing import Protocol, Self, runtime_checkable

from pydantic import BaseModel, model_validator

from bfabric.config.base_url import BaseUrl
from bfabric.config.bfabric_auth import BfabricAuth


@runtime_checkable
class TokenValidationSettingsProtocol(Protocol):
    validation_bfabric_instance: BaseUrl
    supported_bfabric_instances: list[BaseUrl]


class TokenValidationSettings(BaseModel):
    # Canonicalised on parse, so that the operator's chosen form of a trailing slash never decides
    # whether an instance is recognised -- neither here nor in the comparisons downstream.
    validation_bfabric_instance: BaseUrl
    supported_bfabric_instances: list[BaseUrl]

    @model_validator(mode="after")
    def _valid_validation_instance(self) -> Self:
        # NOTE: This could be relaxed in the future, should it become desirable.
        if self.validation_bfabric_instance not in self.supported_bfabric_instances:
            raise ValueError("validation_bfabric_instance must be one of supported_bfabric_instances")
        return self


class WebappIntegrationSettings(TokenValidationSettings):
    feeder_user_credentials: dict[BaseUrl, BfabricAuth]

    @model_validator(mode="after")
    def _valid_feeder_user_credentials(self) -> Self:
        if any(key not in self.supported_bfabric_instances for key in self.feeder_user_credentials):
            raise ValueError("feeder_user_credentials must contain only supported bfabric instances.")
        return self
