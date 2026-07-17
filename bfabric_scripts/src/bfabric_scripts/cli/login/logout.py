"""Logout command — removes an environment (config entry + any cached OAuth tokens)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import cyclopts
import yaml

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile
from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric.config.config_writer import remove_environment_from_config
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice
from bfabric_scripts.cli.login._common import environment_summary
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID


def cmd_login_logout(
    config_env: Annotated[
        str | None,
        cyclopts.Parameter(help="Environment to remove (interactive picker if omitted)."),
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    no_confirm: Annotated[
        bool, cyclopts.Parameter(help="Skip the confirmation prompt (required to remove non-interactively).")
    ] = False,
) -> None:
    """Remove an environment: delete its config entry and clear any cached OAuth tokens.

    With no *config_env*, opens an interactive picker. A non-interactive run must name the
    environment and pass ``--no-confirm`` (it cannot prompt for the destructive confirmation).
    """
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        print(f"Config file not found: {config_path}")
        return

    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    environments = config_file_obj.environments
    names = list(environments)
    if not names:
        print("No environments configured.")
        return

    if config_env is None:
        if not is_interactive():
            print("Specify --config-env to choose an environment to remove non-interactively.", file=sys.stderr)
            return
        width = max(len(name) for name in names)
        default = config_file_obj.general.default_config
        config_env = select_choice(
            "Select the environment to remove",
            names,
            default=default if default in names else None,
            describe=lambda name: f"{name.ljust(width)}   {environment_summary(environments[name])}",
            search=True,
        )
        if config_env is None:
            print("No changes made.")
            return

    if config_env not in environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(names)}")
        return

    env = environments[config_env]
    # Removing the current default clears it (a dangling default makes the config unloadable). Only
    # worth flagging when other environments remain to default to.
    leaves_no_default = config_env == config_file_obj.general.default_config and len(names) > 1

    if not no_confirm:
        if not is_interactive():
            print(
                f"Refusing to remove '{config_env}' without confirmation; pass --no-confirm to proceed.",
                file=sys.stderr,
            )
            return
        prompt = (
            f"Remove environment '{config_env}' ({environment_summary(env)})? "
            "This deletes its config entry and any cached OAuth tokens."
        )
        if leaves_no_default:
            prompt += " It is the current default; afterwards no default will be set."
        if not confirm(prompt):
            print("No changes made.")
            return

    # Remove the config entry first: if that write fails, the cached token is left intact so the
    # environment stays usable, rather than half-removed.
    remove_environment_from_config(config_path, config_env)
    if env.auth_method == "oauth":
        client_id = env.client_id or DEFAULT_CLIENT_ID
        cache_path = compute_token_cache_path(env.config.base_url.rstrip("/"), client_id, config_env).expanduser()
        TokenCache(cache_path).clear()

    print(f"Removed environment '{config_env}'.")
    if leaves_no_default:
        print("It was the default environment; set a new default with 'bfabric-cli auth default <env>'.")
