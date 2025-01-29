from __future__ import annotations

from pathlib import Path

import yaml
from loguru import logger

from bfabric.config import BfabricAuth
from bfabric.config import BfabricClientConfig
from bfabric.config import ConfigFile


def read_config(
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
    logger.debug(f"Reading configuration from: {config_path}")
    config_file = ConfigFile.model_validate(
        yaml.safe_load(Path(config_path).read_text())
    )
    env_config = config_file.get_selected_config(explicit_config_env=config_env)
    return env_config.config, env_config.auth
