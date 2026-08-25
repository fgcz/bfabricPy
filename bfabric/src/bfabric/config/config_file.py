from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Literal, cast

import yaml
from loguru import logger
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_core import PydanticCustomError

from bfabric.config import BfabricAuth, BfabricClientConfig
from bfabric.config.auth_methods import (
    AuthMethod,
    ClientCredentialsAuth,
    ClientRegistration,
    InteractiveOAuthAuth,
    NoAuth,
    UnknownAuth,
    auth_method_from_flat,
    auth_owned_keys,
    registration_from_flat,
)

# Canonical default location of the bfabricPy config file. The tilde is kept unexpanded here;
# callers expand it via Path.expanduser() at the point of use.
DEFAULT_CONFIG_FILE = Path("~/.bfabricpy.yml")


class GeneralConfig(BaseModel):
    default_config: Annotated[str | None, Field(min_length=1)] = None


class EnvironmentConfig(BaseModel):
    config: BfabricClientConfig
    auth_config: AuthMethod = Field(default_factory=NoAuth)
    registration: ClientRegistration | None = None

    @model_validator(mode="before")
    @classmethod
    def split_flat_environment(cls, values: object) -> object:
        """Split a flat YAML environment into client config, auth method and registration."""
        if not isinstance(values, dict):
            return values
        flat = cast("dict[str, object]", values)
        if "auth_config" in flat:
            return flat
        owned = auth_owned_keys()
        return {
            "config": {key: value for key, value in flat.items() if key not in owned},
            "auth_config": auth_method_from_flat(flat),
            "registration": registration_from_flat(flat),
        }

    @property
    def auth(self) -> BfabricAuth | None:
        return self.auth_config.static_auth()

    @property
    def auth_method(self) -> Literal["password", "oauth", "pat", "client_credentials"] | None:
        if isinstance(self.auth_config, NoAuth | UnknownAuth):
            return None
        return self.auth_config.declared_name  # pyright: ignore[reportReturnType]

    @property
    def client_id(self) -> str | None:
        return getattr(self.auth_config, "client_id", None)

    @property
    def client_secret(self) -> SecretStr | None:
        return getattr(self.auth_config, "client_secret", None)

    @property
    def scope(self) -> str | None:
        return getattr(self.auth_config, "scope", None)

    @property
    def registration_access_token(self) -> SecretStr | None:
        return self.registration.registration_access_token if self.registration else None

    @property
    def registration_client_uri(self) -> str | None:
        return self.registration.registration_client_uri if self.registration else None

    def needs_credential_provider(self) -> bool:
        return isinstance(self.auth_config, InteractiveOAuthAuth | ClientCredentialsAuth)


class ConfigFile(BaseModel):
    general: Annotated[GeneralConfig, Field(alias="GENERAL")]
    environments: dict[str, EnvironmentConfig]

    @model_validator(mode="before")
    @classmethod
    def gather_configs(cls, values: object) -> object:
        """Group every non-GENERAL section into ``environments``, without mutating *values*."""
        if not isinstance(values, dict):
            return values
        raw = cast("dict[str, object]", values)
        if "environments" in raw:
            return raw
        return {
            "GENERAL": raw.get("GENERAL", {}),
            "environments": {key: value for key, value in raw.items() if key != "GENERAL"},
        }

    @model_validator(mode="after")
    def validate_default_config(self) -> ConfigFile:
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
        """Return the config environment name: explicit, else ``BFABRICPY_CONFIG_ENV``, else the default."""
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
        """Return the selected environment; see :meth:`get_selected_config_env`."""
        return self.environments[self.get_selected_config_env(explicit_config_env=explicit_config_env)]


def read_config_file(
    config_path: str | Path,
    config_env: str | None = None,
) -> tuple[BfabricClientConfig, BfabricAuth | None]:
    """Read a bfabricPy config file and return the selected environment's ``(config, auth)``.

    :param config_path: Path to the config file (assumed to exist)
    :param config_env: Configuration environment to use; deduced if not given
    """
    logger.debug(f"Reading configuration from: {config_path} {config_env=}")
    config_file = ConfigFile.model_validate(yaml.safe_load(Path(config_path).read_text()))
    env_config = config_file.get_selected_config(explicit_config_env=config_env)
    return env_config.config, env_config.auth
