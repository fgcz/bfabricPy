import json
import os
from pathlib import Path

from pydantic import BaseModel

from bfabric import BfabricClientConfig, BfabricAuth
from bfabric.config.config_file import read_config


class ConfigData(BaseModel):
    client: BfabricClientConfig
    auth: BfabricAuth | None


def load_config_data(config_path: Path | str | None = None) -> ConfigData:
    """Loads the configuration data."""
    if "BFABRICPY_CONFIG_DATA" in os.environ:
        return ConfigData.model_validate_json(os.environ["BFABRICPY_CONFIG_DATA"])

    config_file_path = Path(config_path or "~/.bfabricpy.yml").expanduser()
    if not config_file_path.is_file():
        msg = f"No explicit config provided, and no config file found at {config_file_path}"
        raise OSError(msg)

    config, auth = read_config(config_path=config_file_path, config_env=os.environ.get("BFABRICPY_CONFIG_ENV"))
    return ConfigData(client=config, auth=auth)


def export_config_data(config_data: ConfigData) -> str:
    """Export the config data as a JSON string."""
    auth_data = config_data.auth.model_dump() if config_data.auth else None
    if auth_data is not None:
        auth_data["password"] = auth_data["password"].get_secret_value()
    data = {"client": config_data.client.model_dump(mode="json", round_trip=True), "auth": auth_data}
    return json.dumps(data)
