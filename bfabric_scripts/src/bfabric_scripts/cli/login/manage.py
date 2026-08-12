"""Auth commands over existing config environments — list, activate, status, logout, remove."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Annotated

import cyclopts

from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric.config.config_writer import (
    clear_environment_credentials,
    remove_environment_from_config,
    set_default_config,
)
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice
from bfabric_scripts.cli.login._common import (
    CONFIG_ENV_VAR,
    active_config_env,
    describe_active_reason,
    load_config_file,
    require_mutable_config,
)
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID, SCOPE_PRESETS
from bfabric_scripts.cli.login._urls import instance_host

# Printed on every logout: users reasonably assume it revokes the token server-side too. Says what
# this command does, not what the server can do — instances do advertise a revocation endpoint
# (trace publishes one), we just don't call it.
_NO_REVOCATION_NOTICE = (
    "Note: this removes local credentials only — it does not revoke the token server-side, so any "
    "token already issued stays valid until it expires."
)

_CONFIG_FILE_HELP = "Path to the config file."
_ACTIVATE_ENV_HELP = "Environment to make the default (interactive picker if omitted)."
_LOGOUT_ENV_HELP = "Environment to log out of (default: the active one)."
_ALL_HELP = "Log out of every configured environment."
_REMOVE_ENV_HELP = "Environment to remove (interactive picker if omitted)."
_NO_CONFIRM_HELP = "Skip the confirmation prompt (required to remove non-interactively)."


def _load_config(config_file: Path, *, require_environments: bool = False, mutating: bool = False) -> ConfigFile | None:
    """Load the config file, or print why it is unusable — or unwritable, when *mutating* — and return ``None``."""
    if mutating and not require_mutable_config():
        return None
    config = load_config_file(config_file)
    if config is None:
        print(f"Config file not found: {Path(config_file).expanduser()}")
        return None
    if require_environments and not config.environments:
        print("No environments configured.")
        return None
    return config


def _auth_method(env: EnvironmentConfig) -> str:
    """Effective auth method; legacy envs without ``auth_method`` fall back to ``auth``'s presence."""
    if env.auth_method in ("oauth", "pat"):
        return env.auth_method
    return "password" if env.auth is not None else "none"


def _oauth_cache_path(env: EnvironmentConfig, env_name: str) -> Path:
    """Disk path of *env_name*'s cached OAuth token, keyed by base URL + client ID + env name."""
    client_id = env.client_id or DEFAULT_CLIENT_ID
    return compute_token_cache_path(env.config.base_url, client_id, env_name).expanduser()


def environment_summary(env: EnvironmentConfig) -> str:
    """Compact "host · auth-method" descriptor shown next to an environment name."""
    return f"{instance_host(str(env.config.base_url))} · {_auth_method(env)}"


def _environment_detail(env: EnvironmentConfig, env_name: str, *, now: float) -> str:
    """The scope and token state of one environment, for a listing row."""
    method = _auth_method(env)
    if method != "oauth":
        return method
    cached = TokenCache(_oauth_cache_path(env, env_name)).load()
    if cached is None:
        return "oauth · logged out"
    return f"oauth · {env.scope or '(scope not recorded)'} · {describe_token_cache(cached, now=now)}"


def _select_environment(message: str, config: ConfigFile) -> str | None:
    names = list(config.environments)
    width = max(len(name) for name in names)
    default = config.general.default_config
    return select_choice(
        message,
        names,
        default=default if default in names else None,
        describe=lambda name: f"{name.ljust(width)}   {environment_summary(config.environments[name])}",
        search=True,
    )


def describe_scope(scope: str | None) -> str:
    """Render a scope, appending ``[<preset>]`` on match; ``"(not recorded)"`` if absent."""
    if not scope or not scope.strip():
        return "(not recorded)"
    requested = sorted(scope.split())
    for preset in SCOPE_PRESETS:
        if sorted(preset.scope.split()) == requested:
            return f"{scope}  [{preset.name}]"
    return scope


def describe_token_cache(cached: dict[str, object] | None, *, now: float) -> str:
    """Summarize a cached token: ``missing`` / ``present`` (+ expiry when ``expires_at`` is set)."""
    if cached is None:
        return "missing"
    expires_at = cached.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        return "present"
    remaining = float(expires_at) - now
    if remaining <= 0:
        return "present, expired"
    minutes = int(remaining // 60)
    label = f"~{minutes // 60}h" if minutes >= 60 else f"~{minutes}m"
    return f"present, expires in {label}"


def cmd_auth_list(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help=_CONFIG_FILE_HELP)] = DEFAULT_CONFIG_FILE,
) -> None:
    """List the configured environments, grouped by instance.

    Each row shows the environment's scope and token expiry, and why it is (or isn't) the one in effect.
    """
    config = _load_config(config_file, require_environments=True)
    if config is None:
        return
    environments, default, now = config.environments, config.general.default_config, time.time()
    width = max(len(name) for name in environments)
    by_host: dict[str, list[str]] = {}
    for name, env in environments.items():
        by_host.setdefault(instance_host(str(env.config.base_url)), []).append(name)

    print("Configuration environments:")
    for host, names in by_host.items():
        print(f"\n{host}")
        for name in names:
            marker = "→" if name == default else " "
            detail = _environment_detail(environments[name], name, now=now)
            print(f"{marker} {name.ljust(width)}   {detail}{describe_active_reason(name, default)}")


def cmd_auth_activate(
    config_env: Annotated[str | None, cyclopts.Parameter(help=_ACTIVATE_ENV_HELP)] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help=_CONFIG_FILE_HELP)] = DEFAULT_CONFIG_FILE,
) -> None:
    """Make an environment the default one.

    With no *config_env*, opens an interactive picker in a terminal, or lists the environments
    non-interactively.
    """
    config = _load_config(config_file, require_environments=True, mutating=True)
    if config is None:
        return
    if config_env is None:
        if not is_interactive():
            print("No environment specified. Pass an environment name or run in an interactive terminal.")
            return
        config_env = _select_environment("Select the environment to activate", config)
        if config_env is None:
            print("No changes made.")
            return

    if config_env not in config.environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(config.environments)}")
        return

    set_default_config(config_file, config_env)
    print(f"Activated environment '{config_env}'.")
    if os.environ.get(CONFIG_ENV_VAR) not in (None, config_env):
        print(f"It is not in effect: {CONFIG_ENV_VAR} names a different environment.")


def cmd_auth_status(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help=_CONFIG_FILE_HELP)] = DEFAULT_CONFIG_FILE,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Environment name (default: auto-detect).")] = None,
) -> None:
    """Show current authentication status."""
    config = _load_config(config_file)
    if config is None:
        return
    resolved_env = active_config_env(config_env, config)
    if resolved_env is None:
        print("No environment specified and no default configured.")
        return
    if resolved_env not in config.environments:
        print(f"Environment '{resolved_env}' not found in config.")
        return

    env = config.environments[resolved_env]
    method = _auth_method(env)
    print(f"Environment:  {resolved_env}{describe_active_reason(resolved_env, config.general.default_config)}")
    print(f"Base URL:     {env.config.base_url}")
    print(f"Auth method:  {method}")

    if method == "oauth":
        cache_path = _oauth_cache_path(env, resolved_env)
        print(f"Client ID:    {env.client_id or DEFAULT_CLIENT_ID}")
        print(f"Token cache:  {cache_path} ({describe_token_cache(TokenCache(cache_path).load(), now=time.time())})")
        print(f"Scope:        {describe_scope(env.scope)}")
    elif method == "pat":
        print("Token:        stored in config file")
    elif env.auth is not None:
        print(f"Login:        {env.auth.login}")


def _logout_environment(env: EnvironmentConfig, env_name: str, config_file: Path) -> bool:
    """Remove *env_name*'s credentials — token cache *and* inline YAML secrets — keeping it configured."""
    cleared_keys = clear_environment_credentials(config_file, env_name)
    cache_cleared = False
    if env.auth_method == "oauth":
        cache_path = _oauth_cache_path(env, env_name)
        cache_cleared = cache_path.is_file()
        TokenCache(cache_path).clear()
    if cache_cleared:
        print(f"Cleared the cached OAuth token for '{env_name}'.")
    if cleared_keys:
        print(f"Removed {', '.join(cleared_keys)} from environment '{env_name}'.")
    if not cache_cleared and not cleared_keys:
        print(f"No stored credentials found for '{env_name}'.")
        return False
    return True


def cmd_auth_logout(
    config_env: Annotated[str | None, cyclopts.Parameter(help=_LOGOUT_ENV_HELP)] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help=_CONFIG_FILE_HELP)] = DEFAULT_CONFIG_FILE,
    all_environments: Annotated[bool, cyclopts.Parameter(name=["--all"], help=_ALL_HELP)] = False,
) -> None:
    """Remove stored credentials for this machine, keeping the environment configured.

    Clears the cached OAuth token, or strips an inline PAT / password from the config file. The
    environment survives, so a later ``bfabric-cli login`` can renew it with no arguments; use
    ``auth remove`` to delete it entirely. The token is not revoked server-side, so an already-issued
    token stays valid until it expires — this only removes local access.
    """
    config = _load_config(config_file, require_environments=True, mutating=True)
    if config is None:
        return

    if all_environments:
        names = list(config.environments)
    else:
        # No picker here: an extra prompt when leaving a shared machine is an invitation to skip it.
        resolved = active_config_env(config_env, config)
        if resolved is None:
            print("No environment specified and no default configured.")
            return
        if resolved not in config.environments:
            print(f"Environment '{resolved}' not found. Available environments: {', '.join(config.environments)}")
            return
        names = [resolved]

    # A list, not a generator: ``any`` would short-circuit and ``--all`` would skip the rest.
    cleared = [_logout_environment(config.environments[name], name, config_file) for name in names]
    if any(cleared):
        print(_NO_REVOCATION_NOTICE)


def cmd_auth_remove(
    config_env: Annotated[str | None, cyclopts.Parameter(help=_REMOVE_ENV_HELP)] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help=_CONFIG_FILE_HELP)] = DEFAULT_CONFIG_FILE,
    no_confirm: Annotated[bool, cyclopts.Parameter(help=_NO_CONFIRM_HELP)] = False,
) -> None:
    """Delete an environment: remove its config entry and clear any cached OAuth tokens.

    To keep the environment and only drop its credentials, use ``auth logout`` instead.

    With no *config_env*, opens an interactive picker. A non-interactive run must name the
    environment and pass ``--no-confirm`` (it cannot prompt for the destructive confirmation).
    """
    config = _load_config(config_file, require_environments=True, mutating=True)
    if config is None:
        return
    environments = config.environments

    if config_env is None:
        if not is_interactive():
            print("Specify --config-env to choose an environment to remove non-interactively.", file=sys.stderr)
            return
        config_env = _select_environment("Select the environment to remove", config)
        if config_env is None:
            print("No changes made.")
            return

    if config_env not in environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(environments)}")
        return

    env = environments[config_env]
    # A dangling default makes the config unloadable, so removal clears it; only worth flagging when
    # other environments remain to default to.
    leaves_no_default = config_env == config.general.default_config and len(environments) > 1

    if not no_confirm:
        if not is_interactive():
            print(
                f"Refusing to remove '{config_env}' without confirmation; pass --no-confirm to proceed.",
                file=sys.stderr,
            )
            return
        prompt = (
            f"Remove environment '{config_env}' ({environment_summary(env)})? "
            "This deletes its config entry and any cached OAuth tokens."
        )
        if leaves_no_default:
            prompt += " It is the current default; afterwards no default will be set."
        if not confirm(prompt):
            print("No changes made.")
            return

    # Config entry first: if that write fails the token stays intact, rather than half-removed.
    remove_environment_from_config(config_file, config_env)
    if env.auth_method == "oauth":
        TokenCache(_oauth_cache_path(env, config_env)).clear()

    print(f"Removed environment '{config_env}'.")
    if leaves_no_default:
        print("It was the default environment; set a new default with 'bfabric-cli auth activate <env>'.")
