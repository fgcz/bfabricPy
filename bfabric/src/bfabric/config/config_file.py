from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

import yaml
from loguru import logger
from pydantic import BaseModel, Field, model_validator, field_validator
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
        values["config"] = {key: value for key, value in values.items() if key not in ["login", "password"]}
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

    @field_validator("environments", mode="after")
    @classmethod
    def reject_env_name_default(cls, value: dict[str, EnvironmentConfig]) -> dict[str, EnvironmentConfig]:
        if "default" in value:
            raise ValueError(
                "Environment name 'default' is reserved. Please use a different name for your environment."
            )
        return value

    def get_selected_config_env(self, explicit_config_env: str | None) -> str:
        """Returns the name of the selected configuration, by checking the hierarchy of config_env definitions.
        1. If explicit_config_env is provided, it is used.
        2. If not, secondly, the parser will check if the environment variable `BFABRICPY_CONFIG_ENV` is declared
        3. If not, finally, the parser will select the default_config specified in GENERAL of the .bfabricpy.yml file
        """
        if explicit_config_env:
            return explicit_config_env
        elif "BFABRICPY_CONFIG_ENV" in os.environ:
            logger.debug(f"found BFABRICPY_CONFIG_ENV = {os.environ['BFABRICPY_CONFIG_ENV']}")
            return os.environ["BFABRICPY_CONFIG_ENV"]
        else:
            logger.debug(f"BFABRICPY_CONFIG_ENV not found, using default environment {self.general.default_config}")
            return self.general.default_config

    def get_selected_config(self, explicit_config_env: str | None = None) -> EnvironmentConfig:
        """Returns the selected configuration, by checking the hierarchy of config_env definitions.
        See selected_config_env for details."""
        return self.environments[self.get_selected_config_env(explicit_config_env=explicit_config_env)]


def read_config_file(
    config_path: str | Path,
    config_env: str | None = None,
) -> tuple[BfabricClientConfig, BfabricAuth | None]:
    """
    Reads bfabricpy.yml file, parses it, extracting authentication and configuration data
    :param config_path:   Path to the configuration file. It is assumed the file exists
    :param config_env:    Configuration environment to use. If not given, it is deduced.
    :return: Configuration and Authentication class instances

    NOTE: BFabricPy expects a .bfabricpy.yml of the format, as seen in bfabricPy/tests/unit/example_config.yml
    * The general field always has to be present
    * There may be any number of environments, with arbitrary names. Here, they are called PRODUCTION and TEST
    * Must specify correct login, password and base_url for each environment.
    * application and job_notification_emails fields are optional
    * The default environment will be selected as follows:
        - First, parser will check if the optional argument `config_env` is provided directly to the parser function
        - If not, secondly, the parser will check if the environment variable `BFABRICPY_CONFIG_ENV` is declared
        - If not, finally, the parser will select the default_config specified in [GENERAL] of the .bfabricpy.yml file
    """
    logger.debug(f"Reading configuration from: {config_path} {config_env=}")
    config_file = ConfigFile.model_validate(yaml.safe_load(Path(config_path).read_text()))
    env_config = config_file.get_selected_config(explicit_config_env=config_env)
    return env_config.config, env_config.auth
