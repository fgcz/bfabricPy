"""Auth commands that inspect or manage existing config environments: list, activate, status, logout,
remove. Their shared config-load, environment picker and rendering helpers live here too.
"""

from __future__ import annotations

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
    describe_active_reason,
    load_config_file,
    require_mutable_config,
    resolve_config_env,
)
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID, SCOPE_PRESETS
from bfabric_scripts.cli.login._urls import instance_host

# Said in the command's own output, not just the docs: someone logging out of a shared machine has
# done the responsible thing and would otherwise reasonably believe they were covered.
_NO_REVOCATION_NOTICE = (
    "Note: B-Fabric has no token revocation endpoint, so any token already issued stays valid "
    "server-side until it expires. Local credentials are gone from this machine."
)


def _load_config(config_file: Path, *, require_environments: bool = False) -> ConfigFile | None:
    """Load the config file, or print why it is unusable and return ``None``."""
    config = load_config_file(config_file)
    if config is None:
        print(f"Config file not found: {Path(config_file).expanduser()}")
        return None
    if require_environments and not config.environments:
        print("No environments configured.")
        return None
    return config


def _auth_method(env: EnvironmentConfig) -> str:
    """Effective auth method; falls back to ``auth``'s presence for legacy envs without ``auth_method``."""
    if env.auth_method in ("oauth", "pat"):
        return env.auth_method
    return "password" if env.auth is not None else "none"


def _oauth_cache_path(env: EnvironmentConfig, env_name: str) -> Path:
    """Disk path of *env_name*'s cached OAuth token (keyed by base URL + client ID + env name)."""
    client_id = env.client_id or DEFAULT_CLIENT_ID
    return compute_token_cache_path(env.config.base_url, client_id, env_name).expanduser()


def environment_summary(env: EnvironmentConfig) -> str:
    """A compact "host · auth-method" descriptor shown next to each environment name."""
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


def print_environments(environments: dict[str, EnvironmentConfig], default: str | None, *, now: float) -> None:
    """List the configured environments grouped by host, annotating which one is in effect and why."""
    print("Configuration environments:")
    width = max((len(name) for name in environments), default=0)
    by_host: dict[str, list[str]] = {}
    for name, env in environments.items():
        by_host.setdefault(instance_host(str(env.config.base_url)), []).append(name)
    for host, names in by_host.items():
        print(f"\n{host}")
        for name in names:
            env = environments[name]
            marker = "→" if name == default else " "
            reason = describe_active_reason(name, default)
            print(f"{marker} {name.ljust(width)}   {_environment_detail(env, name, now=now)}{reason}")


def _select_environment(message: str, config: ConfigFile) -> str | None:
    """Interactive picker over the configured environments, each labelled with its host/auth summary."""
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


def describe_scope(scope: object) -> str:
    """Render a scope, appending ``[<preset>]`` on match; ``"(not recorded)"`` if missing/non-string."""
    if not isinstance(scope, str) or not scope.strip():
        return "(not recorded)"
    requested = sorted(scope.split())
    for preset in SCOPE_PRESETS:
        if sorted(preset.scope.split()) == requested:
            return f"{scope}  [{preset.name}]"
    return scope


def describe_token_cache(cached: dict[str, object] | None, *, now: float) -> str:
    """Summarize a cached token's freshness: ``missing`` / ``present`` (+ expiry when ``expires_at`` is set)."""
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
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """List the configured environments, grouped by instance.

    Each row shows the environment's scope and token expiry, and why an environment is the one
    currently in effect — ``BFABRICPY_CONFIG_ENV`` silently outranks the configured default, which is
    otherwise invisible.
    """
    config = _load_config(config_file, require_environments=True)
    if config is None:
        return
    print_environments(config.environments, config.general.default_config, now=time.time())


def cmd_auth_activate(
    config_env: Annotated[
        str | None,
        cyclopts.Parameter(help="Environment to make the default (interactive picker if omitted)."),
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """Make an environment the default one.

    With no *config_env*, opens an interactive picker in a terminal, or lists the environments
    non-interactively.
    """
    if not require_mutable_config():
        return
    config = _load_config(config_file, require_environments=True)
    if config is None:
        return
    names = list(config.environments)

    if config_env is None and is_interactive():
        config_env = _select_environment("Select the environment to activate", config)
    if config_env is None:
        # Cancelled picker, or no TTY to prompt on.
        if is_interactive():
            print("No changes made.")
        else:
            print("No environment specified. Pass an environment name or run in an interactive terminal.")
        return

    if config_env not in config.environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(names)}")
        return

    set_default_config(config_file, config_env)
    print(f"Activated environment '{config_env}'.")
    # An active BFABRICPY_CONFIG_ENV outranks what was just written, which is the whole "I activated
    # it and nothing changed" confusion; say so instead of leaving it to be discovered.
    if describe_active_reason(config_env, config_env) == "":
        print("It is not in effect: BFABRICPY_CONFIG_ENV names a different environment.")


def cmd_auth_status(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Environment name (default: auto-detect).")] = None,
) -> None:
    """Show current authentication status."""
    config = _load_config(config_file)
    if config is None:
        return
    resolved_env = config_env or resolve_config_env(None, config_file)
    if resolved_env is None:
        print("No environment specified and no default configured.")
        return
    if resolved_env not in config.environments:
        print(f"Environment '{resolved_env}' not found in config.")
        return

    env = config.environments[resolved_env]
    print(f"Environment:  {resolved_env}{describe_active_reason(resolved_env, config.general.default_config)}")
    print(f"Base URL:     {env.config.base_url}")
    print(f"Auth method:  {_auth_method(env)}")

    if env.auth_method == "oauth":
        cache_path = _oauth_cache_path(env, resolved_env)
        cached = TokenCache(cache_path).load()
        print(f"Client ID:    {env.client_id or DEFAULT_CLIENT_ID}")
        print(f"Token cache:  {cache_path} ({describe_token_cache(cached, now=time.time())})")
        print(f"Scope:        {describe_scope(env.scope)}")
    elif env.auth_method == "pat":
        print("Token:        stored in config file")
    elif env.auth is not None:
        print(f"Login:        {env.auth.login}")


def _logout_environment(env: EnvironmentConfig, env_name: str, config_file: Path) -> bool:
    """Remove *env_name*'s credentials for this machine, keeping the environment configured.

    "Credentials" differ per auth method: OAuth's live in the token cache, while a PAT and a password
    sit inline in the YAML. A cache-only implementation would report success while leaving a PAT in
    plaintext, so both are handled here.
    """
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
    config_env: Annotated[
        str | None,
        cyclopts.Parameter(help="Environment to log out of (default: the active one)."),
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    all_environments: Annotated[
        bool, cyclopts.Parameter(name=["--all"], help="Log out of every configured environment.")
    ] = False,
) -> None:
    """Remove stored credentials for this machine, keeping the environment configured.

    Clears the cached OAuth token, or strips an inline PAT / password from the config file. The
    environment itself survives, so a later ``bfabric-cli login`` can renew it with no arguments; use
    ``auth remove`` to delete the environment entirely.

    B-Fabric offers no revocation endpoint, so a token that was already issued stays valid until it
    expires — this only removes local access.
    """
    if not require_mutable_config():
        return
    config = _load_config(config_file, require_environments=True)
    if config is None:
        return

    if all_environments:
        names = list(config.environments)
    else:
        # Default to the environment in effect rather than prompting: leaving a shared machine is the
        # case this exists for, and an extra question there is an invitation to skip it.
        resolved = config_env or resolve_config_env(None, config_file)
        if resolved is None:
            print("No environment specified and no default configured.")
            return
        if resolved not in config.environments:
            print(f"Environment '{resolved}' not found. Available environments: {', '.join(config.environments)}")
            return
        names = [resolved]

    # A list, not a generator: ``any`` would stop at the first environment that had credentials, so
    # ``--all`` would silently skip the rest.
    cleared = [_logout_environment(config.environments[name], name, config_file) for name in names]
    if any(cleared):
        print(_NO_REVOCATION_NOTICE)


def cmd_auth_remove(
    config_env: Annotated[
        str | None,
        cyclopts.Parameter(help="Environment to remove (interactive picker if omitted)."),
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    no_confirm: Annotated[
        bool, cyclopts.Parameter(help="Skip the confirmation prompt (required to remove non-interactively).")
    ] = False,
) -> None:
    """Delete an environment: remove its config entry and clear any cached OAuth tokens.

    To keep the environment and only drop its credentials, use ``auth logout`` instead.

    With no *config_env*, opens an interactive picker. A non-interactive run must name the
    environment and pass ``--no-confirm`` (it cannot prompt for the destructive confirmation).
    """
    if not require_mutable_config():
        return
    config = _load_config(config_file, require_environments=True)
    if config is None:
        return
    environments = config.environments
    names = list(environments)

    if config_env is None:
        if not is_interactive():
            print("Specify --config-env to choose an environment to remove non-interactively.", file=sys.stderr)
            return
        config_env = _select_environment("Select the environment to remove", config)
        if config_env is None:
            print("No changes made.")
            return

    if config_env not in environments:
        print(f"Environment '{config_env}' not found. Available environments: {', '.join(names)}")
        return

    env = environments[config_env]
    # Removing the current default clears it (a dangling default makes the config unloadable). Only
    # worth flagging when other environments remain to default to.
    leaves_no_default = config_env == config.general.default_config and len(names) > 1

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

    # Remove the config entry first: if that write fails, the cached token is left intact so the
    # environment stays usable, rather than half-removed.
    remove_environment_from_config(config_file, config_env)
    if env.auth_method == "oauth":
        TokenCache(_oauth_cache_path(env, config_env)).clear()

    print(f"Removed environment '{config_env}'.")
    if leaves_no_default:
        print("It was the default environment; set a new default with 'bfabric-cli auth activate <env>'.")
