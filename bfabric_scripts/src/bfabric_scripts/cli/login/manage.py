"""Auth commands that inspect or manage existing config environments: list, default, status, logout.

Their shared config-load, environment picker, and host/auth/scope rendering helpers live here too.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

import cyclopts
import yaml

from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric.config import DEFAULT_CONFIG_FILE
from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric.config.config_writer import remove_environment_from_config, set_default_config
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice
from bfabric_scripts.cli.login._constants import DEFAULT_CLIENT_ID, SCOPE_PRESETS


def _load_config(config_file: Path) -> ConfigFile | None:
    """Load and validate the config file, or print a "not found" notice and return ``None``."""
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        print(f"Config file not found: {config_path}")
        return None
    return ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))


def _require_environments(config_file: Path) -> ConfigFile | None:
    """Like :func:`_load_config`, but also prints a notice and returns ``None`` if no environments exist."""
    config = _load_config(config_file)
    if config is None:
        return None
    if not config.environments:
        print("No environments configured.")
        return None
    return config


def _auth_method(env: EnvironmentConfig) -> str:
    """Effective auth method; falls back to ``auth``'s presence for legacy envs without ``auth_method``."""
    if env.auth_method in ("oauth", "pat"):
        return env.auth_method
    return "password" if env.auth is not None else "none"


def _oauth_cache_path(env: EnvironmentConfig, env_name: str) -> Path:
    """Disk path of *env_name*'s cached OAuth token (keyed by base URL + client ID)."""
    client_id = env.client_id or DEFAULT_CLIENT_ID
    return compute_token_cache_path(env.config.base_url.rstrip("/"), client_id, env_name).expanduser()


def environment_summary(env: EnvironmentConfig) -> str:
    """A compact "host · auth-method" descriptor shown next to each environment name."""
    base_url = str(env.config.base_url)
    host = urlsplit(base_url).netloc or base_url
    return f"{host} · {_auth_method(env)}"


def print_environments(environments: dict[str, EnvironmentConfig], default: str | None) -> None:
    """List the configured environments with their host/auth summary, marking the default."""
    print("Configuration environments:")
    width = max((len(name) for name in environments), default=0)
    for name, env in environments.items():
        marker, tag = ("→", "  (default)") if name == default else (" ", "")
        print(f"{marker} {name.ljust(width)}   {environment_summary(env)}{tag}")


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


def _normalize_scope(scope: str) -> str:
    """Order-insensitive form of a scope string for comparing against the presets."""
    return " ".join(sorted(scope.split()))


def describe_scope(scope: object) -> str:
    """Render a granted scope, appending ``[<preset>]`` on match; ``"(not recorded)"`` if missing/non-string."""
    if not isinstance(scope, str) or not scope.strip():
        return "(not recorded)"
    normalized = _normalize_scope(scope)
    for preset in SCOPE_PRESETS:
        if _normalize_scope(preset.scope) == normalized:
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
    """List the configured environments, marking the default and showing each host / auth method."""
    config = _require_environments(config_file)
    if config is None:
        return
    print_environments(config.environments, config.general.default_config)


def cmd_auth_default(
    config_env: Annotated[
        str | None,
        cyclopts.Parameter(help="Environment to set as default (interactive picker if omitted)."),
    ] = None,
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
) -> None:
    """Set the default configuration environment.

    With no *config_env*, opens an interactive picker in a terminal, or lists the environments
    non-interactively.
    """
    config = _require_environments(config_file)
    if config is None:
        return
    names = list(config.environments)

    if config_env is None and is_interactive():
        config_env = _select_environment("Select the default environment", config)
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
    print(f"Default environment set to '{config_env}'.")


def cmd_login_status(
    *,
    config_file: Annotated[Path, cyclopts.Parameter(help="Path to the config file.")] = DEFAULT_CONFIG_FILE,
    config_env: Annotated[str | None, cyclopts.Parameter(help="Environment name (default: auto-detect).")] = None,
) -> None:
    """Show current authentication status."""
    config = _load_config(config_file)
    if config is None:
        return
    resolved_env = config_env or os.environ.get("BFABRICPY_CONFIG_ENV") or config.general.default_config
    if resolved_env is None:
        print("No environment specified and no default configured.")
        return
    if resolved_env not in config.environments:
        print(f"Environment '{resolved_env}' not found in config.")
        return

    env = config.environments[resolved_env]
    print(f"Environment:  {resolved_env}")
    print(f"Base URL:     {env.config.base_url}")
    print(f"Auth method:  {_auth_method(env)}")

    if env.auth_method == "oauth":
        client_id = env.client_id or DEFAULT_CLIENT_ID
        cache_path = _oauth_cache_path(env, resolved_env)
        cached = TokenCache(cache_path).load()
        print(f"Client ID:    {client_id}")
        print(f"Token cache:  {cache_path} ({describe_token_cache(cached, now=time.time())})")
        print(f"Scope:        {describe_scope(cached.get('scope') if cached else None)}")
    elif env.auth_method == "pat":
        print("Token:        stored in config file")
    elif env.auth is not None:
        print(f"Login:        {env.auth.login}")


def cmd_login_logout(
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
    """Remove an environment: delete its config entry and clear any cached OAuth tokens.

    With no *config_env*, opens an interactive picker. A non-interactive run must name the
    environment and pass ``--no-confirm`` (it cannot prompt for the destructive confirmation).
    """
    config = _require_environments(config_file)
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
        print("It was the default environment; set a new default with 'bfabric-cli auth default <env>'.")
