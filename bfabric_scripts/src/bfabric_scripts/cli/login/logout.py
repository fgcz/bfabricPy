"""Logout command — clears token cache for an environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import cyclopts
import yaml

from bfabric._oauth._constants import DEFAULT_CLIENT_ID

from bfabric.config.config_file import ConfigFile
from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path


def cmd_login_logout(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = Path("~/.bfabricpy.yml"),
    config_env: Annotated[str | None, cyclopts.Parameter(help="Environment name (default: auto-detect).")] = None,
) -> None:
    """Clear cached OAuth tokens for an environment."""
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
    if env.auth_method == "oauth":
        client_id = env.client_id or DEFAULT_CLIENT_ID
        cache_path = compute_token_cache_path(env.config.base_url.rstrip("/"), client_id, resolved_env).expanduser()
        TokenCache(cache_path).clear()
        print(f"Token cache cleared: {cache_path}")
    else:
        print(f"Environment '{resolved_env}' does not use OAuth; nothing to clear.")
