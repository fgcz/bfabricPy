from __future__ import annotations

import os
from typing import Annotated, Any

from loguru import logger
from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from bfabric.config import BfabricAuth
from bfabric.config import BfabricClientConfig


class GeneralConfig(BaseModel):
    default_config: Annotated[str, Field(min_length=1)]


class EnvironmentConfig(BaseModel):
    config: BfabricClientConfig
    auth: BfabricAuth | None = None

    @model_validator(mode="before")
    @classmethod
    def gather_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Gathers all configs into the config field."""
        if not isinstance(values, dict):
            return values
        values["config"] = {
            key: value
            for key, value in values.items()
            if key not in ["login", "password"]
        }
        return values

    @model_validator(mode="before")
    @classmethod
    def gather_auth(cls, values: dict[str, Any]) -> dict[str, Any]:
        if isinstance(values, dict) and "login" in values:
            values["auth"] = BfabricAuth.model_validate(values)
        return values


class ConfigFile(BaseModel):
    general: Annotated[GeneralConfig, Field(alias="GENERAL")]
    environments: dict[str, EnvironmentConfig]

    @model_validator(mode="before")
    @classmethod
    def gather_configs(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Gathers all configs into the configs field."""
        configs = {}
        for key, value in values.items():
            if key != "GENERAL":
                configs[key] = value
        values["environments"] = configs
        return values

    @model_validator(mode="after")
    def validate_default_config(self) -> ConfigFile:
        """Validates that the default config is specified and is available in the configs."""
        if self.general.default_config not in self.environments:
            raise PydanticCustomError(
                "default_config_not_available",
                "Default config {default_config} not found in {available_configs}",
                {
                    "default_config": self.general.default_config,
                    "available_configs": set(self.environments.keys()),
                },
            )
        return self

    def get_selected_config_env(self, explicit_config_env: str | None) -> str:
        """Returns the name of the selected configuration, by checking the hierarchy of config_env definitions.
        1. If explicit_config_env is provided, it is used.
        2. If not, secondly, the parser will check if the environment variable `BFABRICPY_CONFIG_ENV` is declared
        3. If not, finally, the parser will select the default_config specified in GENERAL of the .bfabricpy.yml file
        """
        if explicit_config_env:
            return explicit_config_env
        elif "BFABRICPY_CONFIG_ENV" in os.environ:
            logger.debug(
                f"found BFABRICPY_CONFIG_ENV = {os.environ['BFABRICPY_CONFIG_ENV']}"
            )
            return os.environ["BFABRICPY_CONFIG_ENV"]
        else:
            logger.debug(
                f"BFABRICPY_CONFIG_ENV not found, using default environment {self.general.default_config}"
            )
            return self.general.default_config

    def get_selected_config(
        self, explicit_config_env: str | None = None
    ) -> EnvironmentConfig:
        """Returns the selected configuration, by checking the hierarchy of config_env definitions.
        See selected_config_env for details."""
        return self.environments[
            self.get_selected_config_env(explicit_config_env=explicit_config_env)
        ]
