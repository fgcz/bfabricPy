"""Device-code login command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth.credential_provider import OAuthCredentialProvider
from bfabric._oauth.device_code import device_code_login
from bfabric._oauth.token_cache import compute_token_cache_path
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import write_environment_to_config
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID, DEFAULT_OAUTH_SCOPE


def cmd_login_device_code(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = DEFAULT_CLIENT_ID,
    config_env: Annotated[str, cyclopts.Parameter(help="Environment name in the config file.")] = "PRODUCTION",
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    scope: Annotated[str, cyclopts.Parameter(help="OAuth scope.")] = DEFAULT_OAUTH_SCOPE,
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for authorization.")] = 600.0,
    set_default: Annotated[
        bool, cyclopts.Parameter(help="Set this environment as the default in the config file.")
    ] = True,
) -> None:
    """Authenticate via device code flow (for headless environments)."""
    import sys

    base_url = base_url.rstrip("/")
    try:
        token = device_code_login(
            base_url,
            client_id=client_id,
            scope=scope,
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
    write_environment_to_config(config_file, config_env, env_data, set_default=set_default)
    print(f"Authenticated successfully.")
    print(f"Config saved to environment '{config_env}' in {config_file}")
