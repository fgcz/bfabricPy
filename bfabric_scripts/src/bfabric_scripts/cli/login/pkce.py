"""PKCE (browser-based) login command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth._constants import DEFAULT_CLIENT_ID, DEFAULT_OAUTH_SCOPE
from bfabric._oauth.credential_provider import OAuthCredentialProvider
from bfabric._oauth.pkce import pkce_login
from bfabric._oauth.token_cache import compute_token_cache_path
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import write_environment_to_config


def cmd_login_pkce(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = DEFAULT_CLIENT_ID,
    config_env: Annotated[str, cyclopts.Parameter(help="Environment name in the config file.")] = "PRODUCTION",
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    scope: Annotated[str, cyclopts.Parameter(help="OAuth scope.")] = DEFAULT_OAUTH_SCOPE,
    port: Annotated[int, cyclopts.Parameter(help="Local port for callback (0 = auto).")] = 0,
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for login.")] = 120.0,
) -> None:
    """Authenticate via browser-based PKCE flow."""
    import sys

    base_url = base_url.rstrip("/")
    print("Opening browser for authentication...", file=sys.stderr)
    print("Waiting for login to complete...", file=sys.stderr)
    try:
        token = pkce_login(
            base_url,
            client_id=client_id,
            scope=scope,
            port=port,
            timeout=timeout,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    cache_path = compute_token_cache_path(base_url, client_id, config_env).expanduser()
    token_url = f"{base_url}/rest/oauth/token"
    # Constructed for its side effect: persists the fresh token to the disk cache.
    _ = OAuthCredentialProvider(
        client_id=client_id,
        client_secret="",
        token_url=token_url,
        token=token,
        grant_type="refresh_token",
        scope=scope,
        token_cache_path=cache_path,
    )
    env_data = {
        "base_url": base_url,
        "auth_method": "oauth",
        "client_id": client_id,
    }
    write_environment_to_config(config_file, config_env, env_data)
    print(f"Authenticated successfully.")
    print(f"Config saved to environment '{config_env}' in {config_file}")
