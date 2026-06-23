"""Register an OAuth client with B-Fabric (RFC 7591)."""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric._oauth.registration import register_client
from bfabric.config import DEFAULT_CONFIG_FILE


def _resolve_token_from_config(config_env: str, config_file: Path) -> tuple[str, str]:
    """Load a cached OAuth access token and base_url for the given environment.

    Returns ``(access_token, base_url)``.
    Raises :class:`SystemExit` on failure.
    """
    import yaml

    from bfabric._oauth._constants import DEFAULT_CLIENT_ID
    from bfabric._oauth.credential_provider import OAuthCredentialProvider
    from bfabric._oauth.token_cache import compute_token_cache_path
    from bfabric.config.config_file import ConfigFile

    config_path = config_file.expanduser()
    if not config_path.is_file():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        raise SystemExit(1)

    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    if config_env not in config_file_obj.environments:
        print(f"Error: Environment '{config_env}' not found in config.", file=sys.stderr)
        raise SystemExit(1)

    env = config_file_obj.environments[config_env]
    base_url = env.config.base_url.rstrip("/")

    if env.auth_method != "oauth":
        print(f"Error: Environment '{config_env}' does not use OAuth.", file=sys.stderr)
        raise SystemExit(1)

    client_id = env.client_id or DEFAULT_CLIENT_ID
    cache_path = compute_token_cache_path(base_url, client_id, config_env).expanduser()
    token_url = f"{base_url}/rest/oauth/token"

    try:
        provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret="",
            token_url=token_url,
            grant_type="refresh_token",
            token_cache_path=cache_path,
        )
        auth = provider.get_auth()
    except Exception as e:
        print(f"Error: Could not obtain token from cached credentials: {e}", file=sys.stderr)
        raise SystemExit(1) from None

    return auth.password.get_secret_value(), base_url


def cmd_login_register(
    client_name: Annotated[str, cyclopts.Parameter(help="Human-readable name for the client.")],
    redirect_uri: Annotated[str, cyclopts.Parameter(help="OAuth redirect URI for the client.")],
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="B-Fabric instance URL (inferred from --config-env if omitted).")
    ] = None,
    *,
    token: Annotated[
        str | None, cyclopts.Parameter(help="Employee Bearer token (prompted if omitted and --config-env not given).")
    ] = None,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Reuse OAuth token from this environment.")] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    service_user: Annotated[
        str | None, cyclopts.Parameter(help="Service user login (enables client_credentials grant).")
    ] = None,
    scope: Annotated[str, cyclopts.Parameter(help="OAuth scope.")] = DEFAULT_OAUTH_SCOPE,
    grant_types: Annotated[
        list[str] | None,
        cyclopts.Parameter(help="Grant types to request (overrides default webapp grants)."),
    ] = None,
) -> None:
    """Register a new OAuth client with the B-Fabric server."""
    resolved_base_url = base_url
    resolved_token = token

    if token is not None:
        print("Warning: passing secrets via CLI flags is insecure (visible in ps, shell history).", file=sys.stderr)
    elif config_env is not None:
        cached_token, cached_base_url = _resolve_token_from_config(config_env, config_file)
        resolved_token = cached_token
        if resolved_base_url is None:
            resolved_base_url = cached_base_url
    else:
        resolved_token = getpass.getpass("Employee Bearer token: ")

    if resolved_base_url is None:
        print("Error: base_url is required when --config-env is not provided.", file=sys.stderr)
        raise SystemExit(1)

    assert resolved_token is not None  # narrowed: set by every branch above

    try:
        result = register_client(
            base_url=resolved_base_url,
            token=resolved_token,
            client_name=client_name,
            redirect_uri=redirect_uri,
            service_user=service_user,
            scope=scope,
            grant_types=grant_types,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2))
