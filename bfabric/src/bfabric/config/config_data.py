from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

from bfabric.config import BfabricClientConfig, BfabricAuth  # noqa
from bfabric.config.config_file import read_config


class ConfigData(BaseModel):
    client: BfabricClientConfig
    auth: BfabricAuth | None

    def drop_auth(self) -> ConfigData:
        """Returns a shallow copy of self with the auth field set to None."""
        return ConfigData(client=self.client, auth=None)


def _read_config_file(config_path: Path | str, fallback_config_env: str | None) -> ConfigData:
    """Reads the config file and returns the config data."""
    config_file_path = Path(config_path).expanduser()
    if not config_file_path.is_file():
        msg = f"No explicit config provided, and no config file found at {config_file_path}"
        raise OSError(msg)

    config, auth = read_config(
        config_path=config_file_path, config_env=fallback_config_env or os.environ.get("BFABRICPY_CONFIG_ENV")
    )
    return ConfigData(client=config, auth=auth)


def load_config_data(
    config_file_path: Path | str, include_auth: bool, config_file_env: str | None = None
) -> ConfigData:
    """Loads the configuration data."""
    if "BFABRICPY_CONFIG_DATA" in os.environ:
        config_data = ConfigData.model_validate_json(os.environ["BFABRICPY_CONFIG_DATA"])
    else:
        config_data = _read_config_file(config_path=config_file_path, fallback_config_env=config_file_env)
    return config_data if include_auth else config_data.drop_auth()


def export_config_data(config_data: ConfigData) -> str:
    """Export the config data as a JSON string."""
    auth_data = config_data.auth.model_dump() if config_data.auth else None
    if auth_data is not None:
        auth_data["password"] = auth_data["password"].get_secret_value()
    data = {"client": config_data.client.model_dump(mode="json", round_trip=True), "auth": auth_data}
    return json.dumps(data)
