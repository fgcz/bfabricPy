"""Interactive OAuth login commands: browser (PKCE) and device-code flows.

They share param resolution and token persistence (``_resolve_params`` / ``_persist``); only the
token-acquisition step differs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth.credential_provider import OAuthCredentialProvider
from bfabric._oauth.device_code import device_code_login
from bfabric._oauth.pkce import pkce_login
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import write_environment_to_config
from bfabric_scripts.cli.login._common import resolve_config_env, resolve_scope, resolve_set_default
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID

_SCOPE_HELP = "Scope preset (read-only|read-write|upload) or a raw scope string (interactive picker if omitted)."
_CONFIG_ENV_HELP = "Environment name (interactive picker: existing or new, if omitted)."
_SET_DEFAULT_HELP = "Set this environment as the default in the config file (prompted if omitted)."


def _resolve_params(
    config_env: str | None, scope: str | None, set_default: bool | None, config_file: Path
) -> tuple[str, str, bool] | None:
    """Resolve env/scope/set-default, or print "Login aborted." and return ``None`` on cancel."""
    config_env = resolve_config_env(config_env, config_file)
    scope = resolve_scope(scope)
    # Only prompt for set-default once env and scope are settled, so a cancel there doesn't prompt.
    set_default = resolve_set_default(set_default, config_env) if config_env and scope else None
    if config_env is None or scope is None or set_default is None:
        print("Login aborted.", file=sys.stderr)
        return None
    return config_env, scope, set_default


def _persist(
    base_url: str,
    client_id: str,
    token: dict[str, object],
    config_env: str,
    config_file: Path,
    set_default: bool,
) -> None:
    """Cache the fresh OAuth *token* and record the environment in the config."""
    _ = OAuthCredentialProvider.cache_login_token(base_url, client_id=client_id, token=token, env_name=config_env)
    env_data = {"base_url": base_url, "auth_method": "oauth", "client_id": client_id}
    write_environment_to_config(config_file, config_env, env_data, set_default=set_default)
    print("Authenticated successfully.")
    print(f"Config saved to environment '{config_env}' in {config_file}")


def cmd_auth_login(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = DEFAULT_CLIENT_ID,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    scope: Annotated[str | None, cyclopts.Parameter(help=_SCOPE_HELP)] = None,
    port: Annotated[int, cyclopts.Parameter(help="Local port for callback (0 = auto).")] = 0,
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for login.")] = 120.0,
    set_default: Annotated[bool | None, cyclopts.Parameter(help=_SET_DEFAULT_HELP)] = None,
) -> None:
    """Authenticate via browser-based login (OAuth PKCE flow)."""
    resolved = _resolve_params(config_env, scope, set_default, config_file)
    if resolved is None:
        return
    config_env, scope, set_default = resolved

    base_url = base_url.rstrip("/")
    print("Opening browser for authentication...", file=sys.stderr)
    print("Waiting for login to complete...", file=sys.stderr)
    try:
        token = pkce_login(base_url, client_id=client_id, scope=scope, port=port, timeout=timeout)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    _persist(base_url, client_id, token, config_env, config_file, set_default)


def cmd_login_device_code(
    base_url: Annotated[str, cyclopts.Parameter(help="B-Fabric instance URL.")],
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = DEFAULT_CLIENT_ID,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    scope: Annotated[str | None, cyclopts.Parameter(help=_SCOPE_HELP)] = None,
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for authorization.")] = 600.0,
    set_default: Annotated[bool | None, cyclopts.Parameter(help=_SET_DEFAULT_HELP)] = None,
) -> None:
    """Authenticate via device code flow (for headless environments)."""
    resolved = _resolve_params(config_env, scope, set_default, config_file)
    if resolved is None:
        return
    config_env, scope, set_default = resolved

    base_url = base_url.rstrip("/")
    try:
        token = device_code_login(base_url, client_id=client_id, scope=scope, timeout=timeout)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    _persist(base_url, client_id, token, config_env, config_file, set_default)
