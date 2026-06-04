"""PAT (Personal Access Token) login command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.config.config_writer import write_environment_to_config


def cmd_login_pat(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    pat: Annotated[str, cyclopts.Parameter(help="Personal Access Token.")],
    *,
    env_name: Annotated[str, cyclopts.Parameter(help="Environment name in the config file.")] = "PRODUCTION",
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = Path("~/.bfabricpy.yml"),
) -> None:
    """Authenticate with a Personal Access Token (PAT)."""
    env_data = {
        "base_url": base_url.rstrip("/"),
        "login": OAUTH_LOGIN,
        "password": pat,
    }
    write_environment_to_config(config_file, env_name, env_data)
    print(f"Authenticated successfully.")
    print(f"Config saved to environment '{env_name}' in {config_file}")
