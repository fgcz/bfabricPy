"""Interactive OAuth login commands: browser (PKCE) and device-code flows.

Both are zero-argument re-loginable: everything a login needs is recorded in the target environment,
so an expired token is replaced by re-running the command with no arguments at all. They share
parameter resolution and token persistence (``_resolve_params`` / ``_persist``); only the
token-acquisition step differs.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth import discovery
from bfabric._oauth.credential_provider import OAuthCredentialProvider
from bfabric._oauth.device_code import device_code_login
from bfabric._oauth.pkce import pkce_login
from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile
from bfabric.config.config_writer import write_environment_to_config
from bfabric_scripts.cli.interactive import confirm, is_interactive
from bfabric_scripts.cli.login._common import (
    load_config_file,
    require_mutable_config,
    resolve_base_url,
    resolve_config_env,
    resolve_scope,
    resolve_set_default,
    suggest_config_env,
)
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID
from bfabric_scripts.cli.login._identity import granted_scope

_SCOPE_HELP = (
    "Scope preset (read-only|read-write|upload) or a raw scope string. "
    "Defaults to the scope recorded for the environment; interactive picker on a first login."
)
_CONFIG_ENV_HELP = "Environment name (defaults to BFABRICPY_CONFIG_ENV or the configured default)."
_SET_DEFAULT_HELP = "Set this environment as the default in the config file (prompted for a new environment)."
_BASE_URL_HELP = "B-Fabric instance URL. Omit to reuse the environment's recorded URL."
_NO_BROWSER_HELP = "Print the authorization URL instead of opening a browser."


@dataclass(frozen=True)
class _LoginParams:
    """Everything a login needs, resolved from the command line, the config, or a prompt."""

    config_env: str
    base_url: str
    scope: str
    set_default: bool


def _confirm_repoint(config_env: str, recorded: str, requested: str) -> bool:
    """Confirm changing an environment's instance URL, which silently repoints every later connect.

    Refuses outright without a terminal: an unattended run pointing ``PRODUCTION`` at a test host is
    exactly the accident worth being loud about.
    """
    print(f"Environment '{config_env}' is currently set to {recorded}.", file=sys.stderr)
    if not is_interactive():
        print(
            f"Refusing to repoint it to {requested} non-interactively. Pass --config-env with a "
            f"different name, or re-run in a terminal to confirm.",
            file=sys.stderr,
        )
        return False
    return confirm(f"Repoint it to {requested}?", default=False) is True


def _resolve_params(
    base_url: str | None,
    config_env: str | None,
    scope: str | None,
    set_default: bool | None,
    config_file: Path,
) -> _LoginParams | None:
    """Resolve the environment, then everything the environment can supply.

    Order matters: the environment is what the base URL and scope are read back from, so it settles
    first — except on a very first login, where there is nothing to read and the name is instead
    derived from the instance that gets picked. Prints "Login aborted." and returns ``None`` on
    cancel or on a refused repoint.
    """
    loaded = load_config_file(config_file)
    existing_names = list(loaded.environments) if loaded else []

    try:
        return _resolve_checked(base_url, config_env, scope, set_default, config_file, loaded, existing_names)
    except ValueError as error:
        # An unusable URL is the user's typo, not a bug: report it like any other rejected input
        # rather than as a traceback.
        print(f"Error: {error}", file=sys.stderr)
        print("Login aborted.", file=sys.stderr)
        return None


def _resolve_checked(
    base_url: str | None,
    config_env: str | None,
    scope: str | None,
    set_default: bool | None,
    config_file: Path,
    loaded: ConfigFile | None,
    existing_names: list[str],
) -> _LoginParams | None:
    """The body of :func:`_resolve_params`, split out so URL validation errors are reported once."""
    first_login = config_env is None and not existing_names
    if first_login:
        resolved_base_url = resolve_base_url(base_url, None)
        if resolved_base_url is None:
            print("No instance selected. Pass the instance URL as an argument.", file=sys.stderr)
            print("Login aborted.", file=sys.stderr)
            return None
        resolved_base_url = _preflight_base_url(resolved_base_url)
        # Derived, not prompted for: a first-time user has no basis for inventing an environment name.
        config_env = suggest_config_env(resolved_base_url, existing_names)
        env = None
    else:
        config_env = resolve_config_env(config_env, config_file)
        if config_env is None:
            print("Login aborted.", file=sys.stderr)
            return None
        env = loaded.environments.get(config_env) if loaded else None

        resolved_base_url = resolve_base_url(base_url, env)
        if resolved_base_url is None:
            print(
                f"No base URL given and environment '{config_env}' has none recorded. "
                f"Pass the instance URL as an argument.",
                file=sys.stderr,
            )
            print("Login aborted.", file=sys.stderr)
            return None

        # Pre-flight *before* comparing against the recorded URL, so a URL discovery would correct
        # (e.g. a host typed without `/bfabric`) isn't mistaken for a deliberate repoint.
        resolved_base_url = _preflight_base_url(resolved_base_url)

        if env is not None and base_url is not None:
            recorded = str(env.config.base_url).rstrip("/")
            if recorded != resolved_base_url and not _confirm_repoint(config_env, recorded, resolved_base_url):
                print("Login aborted.", file=sys.stderr)
                return None

    resolved_scope = resolve_scope(scope, env)
    if resolved_scope is None:
        if not is_interactive():
            print("No scope given and none recorded for this environment. Pass --scope.", file=sys.stderr)
        print("Login aborted.", file=sys.stderr)
        return None

    resolved_set_default = resolve_set_default(set_default, config_env, is_new_env=env is None)
    if resolved_set_default is None:
        print("Login aborted.", file=sys.stderr)
        return None

    return _LoginParams(config_env, resolved_base_url, resolved_scope, resolved_set_default)


def _preflight_base_url(base_url: str) -> str:
    """Check *base_url* against OIDC discovery, correcting a missing ``/bfabric`` if that is the fix.

    Advisory only: an unconfirmed URL is reported and used anyway, since a discovery miss also covers
    an instance that publishes no document. Blocking here would fail a login that would have worked.
    """
    resolved, confirmed = discovery.resolve_base_url(base_url)
    if resolved != base_url:
        print(f"Using {resolved} (no OAuth metadata found at {base_url}).", file=sys.stderr)
    elif not confirmed:
        print(f"Warning: no OAuth metadata found at {base_url}; continuing anyway.", file=sys.stderr)
    return resolved


def _report_scope(params: _LoginParams, client_id: str) -> None:
    """Print the scope being requested, flagging a drop the server made last time.

    A re-login is silent about what it asks for, so someone who once picked ``read-only`` would have
    no way to notice. Comparing the requested scope against the previously *granted* one is what
    makes a server-side drop visible at all.
    """
    print(f"Requesting scope: {params.scope}", file=sys.stderr)
    cache_path = compute_token_cache_path(params.base_url, client_id, params.config_env).expanduser()
    previous = granted_scope(TokenCache(cache_path).load())
    if previous is not None and set(previous.split()) != set(params.scope.split()):
        print(
            f"Note: the previous token was granted '{previous}'. The server drops scopes this client "
            f"is not registered for.",
            file=sys.stderr,
        )


def _persist(
    base_url: str,
    client_id: str,
    token: dict[str, object],
    params: _LoginParams,
    config_file: Path,
) -> None:
    """Cache the fresh OAuth *token* and record the environment as a replayable login recipe."""
    _ = OAuthCredentialProvider.cache_login_token(
        base_url, client_id=client_id, token=token, env_name=params.config_env
    )
    env_data = {
        "base_url": base_url,
        "auth_method": "oauth",
        "client_id": client_id,
        "scope": params.scope,
    }
    write_environment_to_config(config_file, params.config_env, env_data, set_default=params.set_default)
    print("Authenticated successfully.")
    print(f"Config saved to environment '{params.config_env}' in {config_file}")


def cmd_auth_login(
    base_url: Annotated[str | None, cyclopts.Parameter(help=_BASE_URL_HELP)] = None,
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = DEFAULT_CLIENT_ID,
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
    params = _resolve_params(base_url, config_env, scope, set_default, config_file)
    if params is None:
        return

    _report_scope(params, client_id)
    print("Opening browser for authentication...", file=sys.stderr)
    print("Waiting for login to complete...", file=sys.stderr)
    try:
        token = pkce_login(
            params.base_url,
            client_id=client_id,
            scope=params.scope,
            port=port,
            open_browser=not no_browser,
            timeout=timeout,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    _persist(params.base_url, client_id, token, params, config_file)


def cmd_auth_device_code(
    base_url: Annotated[str | None, cyclopts.Parameter(help=_BASE_URL_HELP)] = None,
    *,
    client_id: Annotated[str, cyclopts.Parameter(help="OAuth client ID.")] = DEFAULT_CLIENT_ID,
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
    params = _resolve_params(base_url, config_env, scope, set_default, config_file)
    if params is None:
        return

    _report_scope(params, client_id)
    try:
        token = device_code_login(params.base_url, client_id=client_id, scope=params.scope, timeout=timeout)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from None
    _persist(params.base_url, client_id, token, params, config_file)
