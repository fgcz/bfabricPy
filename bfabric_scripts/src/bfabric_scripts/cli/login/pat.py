"""PAT (Personal Access Token) login command."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_writer import write_environment_to_config


def cmd_login_pat(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    pat: Annotated[str | None, cyclopts.Parameter(help="Personal Access Token (prompted if omitted).")] = None,
    config_env: Annotated[str, cyclopts.Parameter(help="Environment name in the config file.")] = "PRODUCTION",
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = Path("~/.bfabricpy.yml"),
) -> None:
    """Authenticate with a Personal Access Token (PAT)."""
    if pat is None:
        pat = getpass.getpass("Personal Access Token: ")
    else:
        print("Warning: passing secrets via CLI flags is insecure (visible in ps, shell history).", file=sys.stderr)
    env_data = {
        "base_url": base_url.rstrip("/"),
        "login": OAUTH_LOGIN,
        "password": pat,
    }
    write_environment_to_config(config_file, config_env, env_data)
    print("Authenticated successfully.")
    print(f"Config saved to environment '{config_env}' in {config_file}")
