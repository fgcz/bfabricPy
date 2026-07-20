"""PAT (Personal Access Token) login command."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import write_environment_to_config
from bfabric_scripts.cli.login._common import resolve_config_env, resolve_set_default


def cmd_login_pat(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    pat: Annotated[str | None, cyclopts.Parameter(help="Personal Access Token (prompted if omitted).")] = None,
    config_env: Annotated[
        str | None, cyclopts.Parameter(help="Environment name (interactive picker: existing or new, if omitted).")
    ] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    set_default: Annotated[
        bool | None,
        cyclopts.Parameter(help="Set this environment as the default in the config file (prompted if omitted)."),
    ] = None,
) -> None:
    """Authenticate with a Personal Access Token (PAT)."""
    config_env = resolve_config_env(config_env, config_file)
    if config_env is None:
        print("Login aborted.", file=sys.stderr)
        return
    set_default = resolve_set_default(set_default, config_env)
    if set_default is None:
        print("Login aborted.", file=sys.stderr)
        return

    if pat is None:
        pat = getpass.getpass("Personal Access Token: ")
    else:
        print("Warning: passing secrets via CLI flags is insecure (visible in ps, shell history).", file=sys.stderr)
    # Store under ``pat``, not ``login``/``password``: a PAT isn't 32 chars, so an old (<=1.19.0)
    # client eagerly validating every environment would reject a short password and poison the
    # shared config; old clients ignore an unknown ``pat`` key.
    env_data = {
        "base_url": base_url.rstrip("/"),
        "auth_method": "pat",
        "pat": pat,
    }
    write_environment_to_config(config_file, config_env, env_data, set_default=set_default)
    print("Authenticated successfully.")
    print(f"Config saved to environment '{config_env}' in {config_file}")
