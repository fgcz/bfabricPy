"""Command to list the configured environments."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts
import yaml
from rich.console import Console

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile
from bfabric_scripts.cli.login._common import print_environments


def cmd_auth_list(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """List the configured environments, marking the default and showing each host / auth method."""
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        print(f"Config file not found: {config_path}")
        return

    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    if not config_file_obj.environments:
        print("No environments configured.")
        return

    print_environments(Console(), config_file_obj.environments, config_file_obj.general.default_config)
