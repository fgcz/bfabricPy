from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from bfabric.config import BfabricAuth, BfabricClientConfig
from bfabric.config.bfabric_auth import OAUTH_LOGIN

# Canonical default location of the bfabricPy config file. The tilde is kept unexpanded here;
# callers expand it via Path.expanduser() at the point of use.
DEFAULT_CONFIG_FILE = Path("~/.bfabricpy.yml")


class GeneralConfig(BaseModel):
    default_config: Annotated[str | None, Field(min_length=1)] = None


class EnvironmentConfig(BaseModel):
    config: BfabricClientConfig
    auth: BfabricAuth | None = None
    auth_method: Literal["password", "oauth", "pat"] | None = None
    client_id: str | None = None
    scope: str | None = None
    """OAuth scope *requested* at login so a re-login can be replayed without retyping it."""

    @model_validator(mode="before")
    @classmethod
    def gather_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Gathers all configs into the config field."""
        if not isinstance(values, dict):
            return values
        values["config"] = {
            key: value
            for key, value in values.items()  # pyright: ignore[reportAny]
            if key not in ["login", "password", "auth_method", "client_id", "pat", "scope"]
        }
        return values

    @model_validator(mode="before")
    @classmethod
    def gather_auth(cls, values: dict[str, Any]) -> dict[str, Any]:
        if isinstance(values, dict):
            if "login" in values:
                values["auth"] = BfabricAuth.model_validate(values)
            elif values.get("pat"):
                # PAT lives under ``pat`` (not ``login``/``password``) so an unmodified <=1.19.0 client
                # ignores it; shape an OAuth-style auth for the token.
                values["auth"] = BfabricAuth.model_validate({"login": OAUTH_LOGIN, "password": values["pat"]})
            values.pop("pat", None)
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
        if self.general.default_config is not None and self.general.default_config not in self.environments:
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
        """Return the selected config environment name.

        Priority: *explicit_config_env*, then ``BFABRICPY_CONFIG_ENV``, then ``general.default_config``.
        """
        if explicit_config_env:
            return explicit_config_env
        elif "BFABRICPY_CONFIG_ENV" in os.environ:
            logger.debug(f"found BFABRICPY_CONFIG_ENV = {os.environ['BFABRICPY_CONFIG_ENV']}")
            return os.environ["BFABRICPY_CONFIG_ENV"]
        else:
            logger.debug(f"BFABRICPY_CONFIG_ENV not found, using default environment {self.general.default_config}")
            env = self.general.default_config
            if env is None:
                msg = "No environment was specified and no default environment was found."
                raise ValueError(msg)
            return env

    def get_selected_config(self, explicit_config_env: str | None = None) -> EnvironmentConfig:
        """Returns the selected configuration, by checking the hierarchy of config_env definitions.
        See selected_config_env for details."""
        return self.environments[self.get_selected_config_env(explicit_config_env=explicit_config_env)]


def read_config_file(
    config_path: str | Path,
    config_env: str | None = None,
) -> tuple[BfabricClientConfig, BfabricAuth | None]:
    """Read and parse a bfabricPy config file, returning the selected environment's settings.

    :param config_path: Path to the config file (assumed to exist)
    :param config_env: Configuration environment to use; deduced if not given
    :return: The selected environment's ``(config, auth)``
    """
    logger.debug(f"Reading configuration from: {config_path} {config_env=}")
    config_file = ConfigFile.model_validate(yaml.safe_load(Path(config_path).read_text()))
    env_config = config_file.get_selected_config(explicit_config_env=config_env)
    return env_config.config, env_config.auth
