"""Device-code login command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.config.config_writer import write_environment_to_config
from bfabric._oauth.credential_provider import OAuthCredentialProvider
from bfabric._oauth.device_code import device_code_login
from bfabric._oauth.token_cache import compute_token_cache_path


def cmd_login_device_code(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = "bfabric-cli",
    env_name: Annotated[str, cyclopts.Parameter(help="Environment name in the config file.")] = "PRODUCTION",
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = Path("~/.bfabricpy.yml"),
    scope: Annotated[str, cyclopts.Parameter(help="OAuth scope.")] = "api:read api:write",
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for authorization.")] = 600.0,
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
    cache_path = compute_token_cache_path(base_url, client_id, env_name).expanduser()
    token_url = f"{base_url}/rest/oauth/token"
    OAuthCredentialProvider(
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
    write_environment_to_config(config_file, env_name, env_data)
    print(f"Authenticated successfully.")
    print(f"Config saved to environment '{env_name}' in {config_file}")
