from __future__ import annotations

from typing import Self

from pydantic import BaseModel, model_validator

from bfabric.config.bfabric_auth import BfabricAuth  # noqa


class WebappIntegrationSettings(BaseModel):
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
