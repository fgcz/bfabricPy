"""Register an OAuth client with B-Fabric (RFC 7591)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric.oauth import register_client
from bfabric.config import DEFAULT_CONFIG_FILE, BaseUrl
from bfabric_scripts.cli.login._common import FORCE_HELP, SAVE_ENV_HELP, save_registration
from bfabric_scripts.cli.login._constants import DEFAULT_REGISTRATION_SCOPE
from bfabric_scripts.cli.login._urls import normalize_base_url


def _resolve_token_from_config(config_env: str | None, config_file: Path) -> tuple[str, BaseUrl]:
    """The bearer token and base URL of the environment in effect, as ``(token, base_url)``.

    Registration authenticates with a bare bearer token rather than a client, but the token is the one
    ``connect()`` already resolves — so environment precedence, the token cache, and the "log in first"
    errors are shared with the rest of the CLI instead of being reimplemented here.

    :raises SystemExit: ``connect()`` could not authenticate the environment.
    """
    from bfabric import Bfabric

    try:
        client = Bfabric.connect(config_file_path=config_file, config_file_env=config_env or "default")
        return client.auth.password.get_secret_value(), client.config.base_url
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None


def cmd_login_register(
    client_name: Annotated[str, cyclopts.Parameter(help="Human-readable name for the client.")],
    redirect_uri: Annotated[str, cyclopts.Parameter(help="OAuth redirect URI for the client.")],
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="B-Fabric instance URL (inferred from --config-env if omitted).")
    ] = None,
    *,
    token: Annotated[
        str | None,
        cyclopts.Parameter(help="Employee Bearer token (defaults to the logged-in environment's token)."),
    ] = None,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Reuse OAuth token from this environment.")] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    service_user: Annotated[
        str | None, cyclopts.Parameter(help="Service user login (enables client_credentials grant).")
    ] = None,
    no_service_user: Annotated[
        bool,
        cyclopts.Parameter(
            help="Explicitly register without a service user (no client_credentials grant).",
            negative=(),
        ),
    ] = False,
    scope: Annotated[str, cyclopts.Parameter(help="OAuth scope.")] = DEFAULT_REGISTRATION_SCOPE,
    grant_types: Annotated[
        list[str] | None,
        cyclopts.Parameter(help="Grant types to request (overrides default webapp grants)."),
    ] = None,
    save_env: Annotated[str | None, cyclopts.Parameter(help=SAVE_ENV_HELP)] = None,
    force: Annotated[bool, cyclopts.Parameter(help=FORCE_HELP, negative=())] = False,
) -> None:
    """Register a new OAuth client with the B-Fabric server.

    :param save_env: Save the new client to this config environment, including its RFC 7591
        registration credentials so it can be edited later. Omit to only print the response.
    """
    if service_user is not None and no_service_user:
        print("Error: --service-user and --no-service-user are mutually exclusive.", file=sys.stderr)
        raise SystemExit(1)
    if service_user is None and not no_service_user:
        print(
            "Error: pass --service-user LOGIN to enable the client_credentials grant, "
            "or --no-service-user to register without one.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    resolved_base_url = normalize_base_url(base_url) if base_url is not None else None
    resolved_token = token

    if token is not None:
        print("Warning: passing secrets via CLI flags is insecure (visible in ps, shell history).", file=sys.stderr)
    else:
        # No token given: authenticate as the environment in effect, like every other `auth` command.
        cached_token, cached_base_url = _resolve_token_from_config(config_env, config_file)
        resolved_token = cached_token
        if resolved_base_url is None:
            resolved_base_url = cached_base_url

    if resolved_base_url is None:
        print("Error: base_url is required when --token is given.", file=sys.stderr)
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

    if save_env is not None:
        save_registration(
            result,
            base_url=resolved_base_url,
            config_file=config_file,
            env_name=save_env,
            is_service_account=service_user is not None,
            force=force,
        )
