"""Login status command."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import cyclopts
import yaml

from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile
from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID


def cmd_login_status(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Environment name (default: auto-detect).")] = None,
) -> None:
    """Show current authentication status."""
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        print(f"Config file not found: {config_path}")
        return

    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    resolved_env = config_env or os.environ.get("BFABRICPY_CONFIG_ENV") or config_file_obj.general.default_config
    if resolved_env is None:
        print("No environment specified and no default configured.")
        return

    if resolved_env not in config_file_obj.environments:
        print(f"Environment '{resolved_env}' not found in config.")
        return

    env = config_file_obj.environments[resolved_env]
    print(f"Environment:  {resolved_env}")
    print(f"Base URL:     {env.config.base_url}")

    if env.auth_method == "oauth":
        client_id = env.client_id or DEFAULT_CLIENT_ID
        print(f"Auth method:  oauth")
        print(f"Client ID:    {client_id}")
        cache_path = compute_token_cache_path(env.config.base_url.rstrip("/"), client_id, resolved_env).expanduser()
        cached = TokenCache(cache_path).load()
        if cached:
            print(f"Token cache:  {cache_path} (present)")
        else:
            print(f"Token cache:  {cache_path} (missing)")
    elif env.auth_method == "pat":
        print("Auth method:  pat")
        print("Token:        stored in config file")
    elif env.auth is not None:
        print(f"Auth method:  password")
        print(f"Login:        {env.auth.login}")
    else:
        print("Auth method:  none")
