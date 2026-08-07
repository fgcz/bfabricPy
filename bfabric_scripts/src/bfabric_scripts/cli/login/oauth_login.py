"""Interactive OAuth login commands: browser (PKCE) and device-code flows.

Both are zero-argument re-loginable: everything a login needs is recorded in the target environment.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth.credential_provider import OAuthCredentialProvider
from bfabric._oauth.device_code import device_code_login
from bfabric._oauth.pkce import pkce_login
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_writer import write_environment_to_config
from bfabric_scripts.cli.interactive import confirm, is_interactive
from bfabric_scripts.cli.login._common import (
    load_config_file,
    require_mutable_config,
    resolve_base_url,
    resolve_config_env,
    resolve_scope,
    resolve_set_default,
)
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID
from bfabric_scripts.cli.login._urls import normalize_base_url, suggest_env_name

_SCOPE_HELP = (
    "Scope preset (read-only|read-write|upload) or a raw scope string. "
    "Defaults to the scope recorded for the environment; interactive picker on a first login."
)
_CONFIG_ENV_HELP = "Environment name (defaults to BFABRICPY_CONFIG_ENV or the configured default)."
_SET_DEFAULT_HELP = "Set this environment as the default in the config file (prompted for a new environment)."
_BASE_URL_HELP = "B-Fabric instance URL. Omit to reuse the environment's recorded URL."
_NO_BROWSER_HELP = "Print the authorization URL instead of opening a browser."
_CLIENT_ID_HELP = "OAuth client ID. Omit to reuse the environment's recorded ID, or the default 'CLI'."


@dataclass(frozen=True)
class _LoginParams:
    """Everything a login needs, resolved from the command line, config, or a prompt."""

    config_env: str
    base_url: str
    client_id: str
    scope: str
    set_default: bool


def _confirm_repoint(config_env: str, recorded: str, requested: str) -> bool:
    """Confirm repointing an environment's instance URL — it silently redirects every later connect."""
    print(f"Environment '{config_env}' is currently set to {recorded}.", file=sys.stderr)
    if not is_interactive():
        print(
            f"Refusing to repoint it to {requested} non-interactively. Pass --config-env with a "
            f"different name, or re-run in a terminal to confirm.",
            file=sys.stderr,
        )
        return False
    return confirm(f"Repoint it to {requested}?", default=False) is True


def _abort(message: str | None = None) -> None:
    if message is not None:
        print(message, file=sys.stderr)
    print("Login aborted.", file=sys.stderr)


def _resolve_params(
    base_url: str | None,
    client_id: str | None,
    config_env: str | None,
    scope: str | None,
    set_default: bool | None,
    config_file: Path,
) -> _LoginParams | None:
    """Resolve the environment, then everything the environment can supply; ``None`` to abort.

    Order matters: base URL and scope are read back from the environment, so it settles first.
    """
    loaded = load_config_file(config_file)
    existing_names = list(loaded.environments) if loaded else []
    env = None

    try:
        if config_env is None and not existing_names:
            resolved_base_url = resolve_base_url(base_url, None)
            if resolved_base_url is None:
                _abort("No instance selected. Pass the instance URL as an argument.")
                return None
            # Derived, not prompted: a first-time user has no basis for inventing a name.
            config_env = suggest_env_name(resolved_base_url)
        else:
            config_env = resolve_config_env(config_env, config_file)
            if config_env is None:
                _abort()
                return None
            env = loaded.environments.get(config_env) if loaded else None

            resolved_base_url = resolve_base_url(base_url, env)
            if resolved_base_url is None:
                _abort(
                    f"No base URL given and environment '{config_env}' has none recorded. "
                    f"Pass the instance URL as an argument."
                )
                return None

            if env is not None and base_url is not None:
                recorded = normalize_base_url(str(env.config.base_url))
                if recorded != resolved_base_url and not _confirm_repoint(config_env, recorded, resolved_base_url):
                    _abort()
                    return None
    except ValueError as error:
        # A typo, not a bug: report it as rejected input.
        _abort(f"Error: {error}")
        return None

    resolved_scope = resolve_scope(scope, env)
    if resolved_scope is None:
        _abort("No scope given and none recorded for this environment. Pass --scope." if not is_interactive() else None)
        return None

    resolved_set_default = resolve_set_default(set_default, config_env, is_new_env=env is None)
    if resolved_set_default is None:
        _abort()
        return None

    # Reuse the recorded ID so a non-default client registration survives a re-login.
    resolved_client_id = client_id or (env.client_id if env is not None else None) or DEFAULT_CLIENT_ID
    return _LoginParams(config_env, resolved_base_url, resolved_client_id, resolved_scope, resolved_set_default)


def _persist(token: dict[str, object], params: _LoginParams, config_file: Path) -> None:
    """Cache the fresh OAuth *token* and record the environment as a replayable login recipe."""
    _ = OAuthCredentialProvider.cache_login_token(
        params.base_url, client_id=params.client_id, token=token, env_name=params.config_env
    )
    env_data = {
        "base_url": params.base_url,
        "auth_method": "oauth",
        "client_id": params.client_id,
        "scope": params.scope,
    }
    write_environment_to_config(config_file, params.config_env, env_data, set_default=params.set_default)
    print("Authenticated successfully.")
    print(f"Config saved to environment '{params.config_env}' in {config_file}")


def cmd_auth_login(
    base_url: Annotated[str | None, cyclopts.Parameter(help=_BASE_URL_HELP)] = None,
    *,
    client_id: Annotated[str | None, cyclopts.Parameter(help=_CLIENT_ID_HELP)] = None,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    scope: Annotated[str | None, cyclopts.Parameter(help=_SCOPE_HELP)] = None,
    port: Annotated[int, cyclopts.Parameter(help="Local port for callback (0 = auto).")] = 0,
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for login.")] = 120.0,
    no_browser: Annotated[bool, cyclopts.Parameter(help=_NO_BROWSER_HELP)] = False,
    set_default: Annotated[bool | None, cyclopts.Parameter(help=_SET_DEFAULT_HELP)] = None,
) -> None:
    """Authenticate via browser-based login (OAuth PKCE flow).

    Run with no arguments to renew an expired login: the instance URL and scope are read back from
    the environment. The browser must be on this machine, because the login is completed through a
    redirect to a local port — over SSH, use ``auth device-code`` instead.
    """
    if not require_mutable_config():
        return
    params = _resolve_params(base_url, client_id, config_env, scope, set_default, config_file)
    if params is None:
        return

    print(f"Requesting scope: {params.scope}", file=sys.stderr)
    print("Opening browser for authentication...", file=sys.stderr)
    print("Waiting for login to complete...", file=sys.stderr)
    try:
        token = pkce_login(
            params.base_url,
            client_id=params.client_id,
            scope=params.scope,
            port=port,
            open_browser=not no_browser,
            timeout=timeout,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    _persist(token, params, config_file)


def cmd_auth_device_code(
    base_url: Annotated[str | None, cyclopts.Parameter(help=_BASE_URL_HELP)] = None,
    *,
    client_id: Annotated[str | None, cyclopts.Parameter(help=_CLIENT_ID_HELP)] = None,
    config_env: Annotated[str | None, cyclopts.Parameter(help=_CONFIG_ENV_HELP)] = None,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    scope: Annotated[str | None, cyclopts.Parameter(help=_SCOPE_HELP)] = None,
    timeout: Annotated[float, cyclopts.Parameter(help="Seconds to wait for authorization.")] = 600.0,
    set_default: Annotated[bool | None, cyclopts.Parameter(help=_SET_DEFAULT_HELP)] = None,
) -> None:
    """Authenticate via device code flow, for headless and remote environments.

    Run with no arguments to renew an expired login. Unlike the browser flow this needs no local
    port, so the code can be entered in a browser on any machine.
    """
    if not require_mutable_config():
        return
    params = _resolve_params(base_url, client_id, config_env, scope, set_default, config_file)
    if params is None:
        return

    print(f"Requesting scope: {params.scope}", file=sys.stderr)
    try:
        token = device_code_login(params.base_url, client_id=params.client_id, scope=params.scope, timeout=timeout)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    _persist(token, params, config_file)
