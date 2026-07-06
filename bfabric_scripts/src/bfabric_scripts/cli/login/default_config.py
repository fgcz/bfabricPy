"""Commands to show and set the default configuration environment."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts
import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile
from bfabric.config.config_writer import set_default_config

cmd_auth_default = cyclopts.App(help="Show or set the default configuration environment.")


def _environment_line(name: str, *, index: int | None, is_default: bool) -> Text:
    """Render one environment row. Text (not markup) keeps names with "[" literal.

    The current default is prefixed with a bold-green arrow so it stands out in a long list.
    """
    label = f"{index}. {name}" if index is not None else name
    if is_default:
        # Chained appends (each returns the Text) keep the whole row in one expression.
        return Text("→ ", style="bold green").append(label, style="bold green").append("  (default)", style="green")
    return Text(f"  {label}")


def _prompt_for_environment(console: Console, names: list[str], default: str | None) -> str:
    """Show a numbered menu of *names* and return the environment the user picks."""
    console.print("Configuration environments:")
    for index, name in enumerate(names, start=1):
        console.print(_environment_line(name, index=index, is_default=name == default))
    choices = [str(i) for i in range(1, len(names) + 1)]
    # show_choices=False: the numbered menu above already lists the options, so the prompt stays
    # short ("Select environment (3):") instead of repeating every name inline. Only offer a
    # default when there is a current default to pre-select; otherwise the pick is required.
    if default in names:
        answer = Prompt.ask(
            "Select environment", choices=choices, default=str(names.index(default) + 1), show_choices=False
        )
    else:
        answer = Prompt.ask("Select environment", choices=choices, show_choices=False)
    return names[int(answer) - 1]


@cmd_auth_default.default
def cmd_auth_default_show(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """List configuration environments and show the current default."""
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
    console = Console()
    console.print("Configuration environments:")
    for name in names:
        console.print(_environment_line(name, index=None, is_default=name == default))
    if default is None:
        console.print("\nNo default configured.")


@cmd_auth_default.command(name="set")
def cmd_auth_default_set(
    config_env: Annotated[
        str | None, cyclopts.Parameter(help="Environment to set as default (prompted if omitted).")
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """Set the default configuration environment."""
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        print(f"Config file not found: {config_path}")
        return

    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    names = list(config_file_obj.environments)
    if not names:
        print("No environments configured.")
        return

    if config_env is None:
        config_env = _prompt_for_environment(Console(), names, config_file_obj.general.default_config)

    if config_env not in config_file_obj.environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(names)}")
        return

    set_default_config(config_path, config_env)
    print(f"Default environment set to '{config_env}'.")
