from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

import yaml
from loguru import logger
from pydantic import BaseModel

from bfabric.config import BfabricClientConfig, BfabricAuth
from bfabric.config.config_file import ConfigFile


class ConfigData(BaseModel):
    client: BfabricClientConfig
    auth: BfabricAuth | None
    auth_method: Literal["password", "oauth"] | None = None
    client_id: str | None = None
    env_name: str | None = None

    def with_auth(self, auth: BfabricAuth | None) -> ConfigData:
        """Returns a shallow copy of self with the auth field set to the specified value."""
        return ConfigData(
            client=self.client,
            auth=auth,
            auth_method=self.auth_method,
            client_id=self.client_id,
            env_name=self.env_name,
        )


def _read_config_file(config_path: Path | str, force_config_env: str | None) -> ConfigData:
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
        auth_method=env_config.auth_method,
        client_id=env_config.client_id,
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
        config_data = _read_config_file(config_path=config_file_path, force_config_env=config_file_env)
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
