from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import yaml
from loguru import logger
from pydantic import BaseModel, Field, model_validator

from bfabric.config import BfabricClientConfig, BfabricAuth
from bfabric.config.auth_methods import AuthMethod, AuthMethodName, NoAuth, auth_method_from_flat
from bfabric.config.config_file import ConfigFile

if TYPE_CHECKING:
    from bfabric.oauth._credential_provider import OAuthCredentialProvider

# The flat auth keys accepted by the constructor and carried in the override JSON.
_FLAT_AUTH_KEYS = ("auth_method", "client_id")


class ConfigData(BaseModel):
    client: BfabricClientConfig
    auth: BfabricAuth | None
    auth_config: AuthMethod = Field(default_factory=NoAuth)
    """How this environment authenticates, beyond the static credentials in :attr:`auth`."""
    env_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _gather_auth_config(cls, values: object) -> object:
        """Accept the flat ``auth_method``/``client_id`` kwargs the override JSON carries."""
        if not isinstance(values, dict):
            return values
        raw = cast("dict[str, object]", values)
        if "auth_config" in raw or not any(raw.get(key) is not None for key in _FLAT_AUTH_KEYS):
            return raw
        rest = {key: value for key, value in raw.items() if key not in _FLAT_AUTH_KEYS}
        return {**rest, "auth_config": auth_method_from_flat(raw)}

    @property
    def auth_method(self) -> AuthMethodName | None:
        return self.auth_config.declared_name

    @property
    def client_id(self) -> str | None:
        return getattr(self.auth_config, "client_id", None)

    def credential_provider(self) -> OAuthCredentialProvider | None:
        """A token-refreshing provider, for the auth methods that need one.

        ``password`` and ``pat`` authenticate from :attr:`auth` and need none.
        """
        return self.auth_config.credential_provider(base_url=self.client.base_url, env_name=self.env_name)

    def with_auth(self, auth: BfabricAuth | None) -> ConfigData:
        """Returns a shallow copy of self with the auth field set to the specified value."""
        return self.model_copy(update={"auth": auth})


def _load_environment_config_data(config_path: Path | str, force_config_env: str | None) -> ConfigData:
    """Reads the config file and returns the config data."""
    config_file_path = Path(config_path).expanduser()
    if not config_file_path.is_file():
        msg = f"No explicit config provided, and no config file found at {config_file_path}"
        raise OSError(msg)

    config_env = force_config_env or os.environ.get("BFABRICPY_CONFIG_ENV")
    logger.debug(f"Reading configuration from: {config_file_path} {config_env=}")
    config_file = ConfigFile.model_validate(yaml.safe_load(config_file_path.read_text()))
    resolved_env = config_file.get_selected_config_env(explicit_config_env=config_env)
    env_config = config_file.environments[resolved_env]
    return ConfigData(
        client=env_config.config,
        auth=env_config.auth,
        auth_config=env_config.auth_config,
        env_name=resolved_env,
    )


def load_config_data(
    config_file_path: Path | str,
    config_file_env: str | Literal["default"] | None,
    include_auth: bool,
) -> ConfigData:
    """Loads the configuration data."""
    if "BFABRICPY_CONFIG_OVERRIDE" in os.environ:
        config_data = ConfigData.model_validate_json(os.environ["BFABRICPY_CONFIG_OVERRIDE"])
    elif config_file_env is not None:
        config_file_env = os.environ.get("BFABRICPY_CONFIG_ENV") if config_file_env == "default" else config_file_env
        config_data = _load_environment_config_data(config_path=config_file_path, force_config_env=config_file_env)
    else:
        msg = "No configuration was found and config_file_env is set to None."
        raise ValueError(msg)
    return config_data if include_auth else config_data.with_auth(None)


def export_config_data(config_data: ConfigData) -> str:
    """Export the config data as a JSON string."""
    auth_data = config_data.auth.model_dump() if config_data.auth else None
    if auth_data is not None:
        auth_data["password"] = auth_data["password"].get_secret_value()
    data = {
        "client": config_data.client.model_dump(mode="json", round_trip=True),
        "auth": auth_data,
        "auth_method": config_data.auth_method,
        "client_id": config_data.client_id,
        "env_name": config_data.env_name,
    }
    return json.dumps(data)
