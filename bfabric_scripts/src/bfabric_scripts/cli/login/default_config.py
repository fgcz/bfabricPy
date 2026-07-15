"""Command to show and set the default configuration environment."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts
import yaml
from rich.console import Console

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile
from bfabric.config.config_writer import set_default_config
from bfabric_scripts.cli.interactive import is_interactive, resolve_choice
from bfabric_scripts.cli.login._common import environment_summary, print_environments


def cmd_auth_default(
    config_env: Annotated[
        str | None,
        cyclopts.Parameter(help="Environment to set as default (interactive picker if omitted)."),
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """Set the default configuration environment.

    With no *config_env*, opens an interactive picker (arrow keys to navigate, Enter to select)
    in a terminal, or lists the environments in a non-interactive context.
    """
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        print(f"Config file not found: {config_path}")
        return

    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    names = list(config_file_obj.environments)
    if not names:
        print("No environments configured.")
        return

    default = config_file_obj.general.default_config
    width = max(len(name) for name in names)
    config_env = resolve_choice(
        config_env,
        names,
        message="Select the default environment",
        default=default if default in names else None,
        describe=lambda name: f"{name.ljust(width)}   {environment_summary(config_file_obj.environments[name])}",
        search=True,
    )
    if config_env is None:
        # None means either the user cancelled the picker or there is no TTY to prompt on.
        console = Console()
        if is_interactive():
            console.print("No changes made.")
        else:
            print_environments(console, config_file_obj.environments, default)
            console.print("Run in an interactive terminal or pass an environment name to set the default.")
        return

    if config_env not in config_file_obj.environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(names)}")
        return

    set_default_config(config_path, config_env)
    print(f"Default environment set to '{config_env}'.")
