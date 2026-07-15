"""Shared helpers for the ``auth`` command group.

Covers parameter resolution for the login commands (environment name and OAuth scope may be
given on the command line, picked interactively, or -- for the environment -- typed as a new
value) plus the rendering used by ``auth default`` / ``auth list`` / ``auth status``, so the
individual commands don't each re-implement it.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml
from rich.console import Console
from rich.text import Text

from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric_scripts.cli.interactive import confirm, is_interactive, resolve_choice, select_choice, text_input
from bfabric_scripts.cli.login._constants import (
    DEFAULT_LOGIN_SCOPE,
    DEFAULT_SCOPE_PRESET,
    SCOPE_PRESETS,
    SCOPE_PRESETS_BY_NAME,
)

# Interactive-only sentinel: choosing it opens a free-text prompt for raw scopes.
_CUSTOM = "custom"

# Fallback environment name when none is configured and none is given (historical default).
_FALLBACK_ENV = "PRODUCTION"


def _existing_environments(config_file: Path) -> tuple[list[str], str | None]:
    """Return the configured environment names and the current default (``[]``, ``None`` if absent)."""
    config_path = Path(config_file).expanduser()
    if not config_path.is_file():
        return [], None
    config_file_obj = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
    return list(config_file_obj.environments), config_file_obj.general.default_config


def resolve_config_env(config_env: str | None, config_file: Path) -> str | None:
    """Resolve the target environment name.

    * *config_env* given -> use it verbatim.
    * no TTY -> the current default environment if set, else ``"PRODUCTION"``.
    * otherwise -> interactive picker: choose an existing environment or type a new name,
      prefilled with that same fallback. Returns ``None`` if the user cancels.
    """
    if config_env is not None:
        return config_env
    names, current = _existing_environments(config_file)
    fallback = current or _FALLBACK_ENV
    if not is_interactive():
        return fallback
    return resolve_choice(None, names, message="Environment name", allow_new=True, default=fallback)


def _scope_menu_label(choice: str) -> str:
    """Menu label for a scope preset (description + the scopes it maps to) or the Custom entry."""
    width = max(len(preset.description) for preset in SCOPE_PRESETS)
    if choice == _CUSTOM:
        return f"{'Custom…'.ljust(width)}   (enter scopes manually)"
    preset = SCOPE_PRESETS_BY_NAME[choice]
    return f"{preset.description.ljust(width)}   {preset.scope}"


def resolve_scope(scope: str | None) -> str | None:
    """Resolve the OAuth scope string.

    * *scope* given -> a preset name expands to its scope string; anything else passes through
      as a raw space-separated scope string.
    * no TTY -> the ``read-write`` default (``DEFAULT_LOGIN_SCOPE``).
    * otherwise -> interactive picker of the named presets plus a Custom option that opens a
      free-text prompt. Returns ``None`` if the user cancels.
    """
    if scope is not None:
        preset = SCOPE_PRESETS_BY_NAME.get(scope)
        return preset.scope if preset is not None else scope
    if not is_interactive():
        return DEFAULT_LOGIN_SCOPE
    picked = select_choice(
        "Select OAuth scope set",
        [preset.name for preset in SCOPE_PRESETS] + [_CUSTOM],
        default=DEFAULT_SCOPE_PRESET,
        describe=_scope_menu_label,
    )
    if picked is None:
        return None
    if picked == _CUSTOM:
        return text_input("Enter OAuth scopes (space-separated)", default=DEFAULT_LOGIN_SCOPE)
    return SCOPE_PRESETS_BY_NAME[picked].scope


def resolve_set_default(set_default: bool | None, config_env: str) -> bool | None:
    """Resolve whether the freshly-authenticated environment becomes the config default.

    * explicit ``--set-default`` / ``--no-set-default`` (i.e. not ``None``) -> honored verbatim.
    * otherwise, no TTY -> ``True`` (the historical default).
    * otherwise -> a yes/no prompt, preselected yes; ``None`` if the user cancels (the caller aborts).
    """
    if set_default is not None:
        return set_default
    if not is_interactive():
        return True
    return confirm(f"Set '{config_env}' as the default environment?", default=True)


def _normalize_scope(scope: str) -> str:
    """Order-insensitive form of a scope string for comparing against the presets."""
    return " ".join(sorted(scope.split()))


def describe_scope(scope: object) -> str:
    """Render a granted OAuth scope for display, annotated with its preset name if it matches.

    * a scope equal to a preset (order-insensitive) -> ``"<scopes>  [<preset>]"``
    * any other non-empty scope -> the raw string
    * missing / non-string (a cache without a recorded scope) -> ``"(not recorded)"``
    """
    if not isinstance(scope, str) or not scope.strip():
        return "(not recorded)"
    normalized = _normalize_scope(scope)
    for preset in SCOPE_PRESETS:
        if _normalize_scope(preset.scope) == normalized:
            return f"{scope}  [{preset.name}]"
    return scope


def _format_duration(seconds: float) -> str:
    """A coarse ``~1h05m`` / ``~7m`` / ``<1m`` label for a positive remaining duration."""
    minutes = int(seconds // 60)
    if minutes >= 60:
        hours, mins = divmod(minutes, 60)
        return f"~{hours}h{mins:02d}m"
    if minutes >= 1:
        return f"~{minutes}m"
    return "<1m"


def describe_token_cache(cached: dict[str, object] | None, *, now: float) -> str:
    """Summarize a cached OAuth token's freshness.

    ``"missing"`` when absent; otherwise ``"present"``, extended with ``expired`` or
    ``expires in ~…`` when the token carries a numeric ``expires_at`` (Unix seconds).
    """
    if cached is None:
        return "missing"
    expires_at = cached.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        return "present"
    remaining = float(expires_at) - now
    if remaining <= 0:
        return "present, expired"
    return f"present, expires in {_format_duration(remaining)}"


def auth_method_label(env: EnvironmentConfig) -> str:
    """Label an environment's auth method, mirroring ``auth status``' precedence."""
    if env.auth_method in ("oauth", "pat"):
        return env.auth_method
    if env.auth is not None:
        return "password"
    return "none"


def environment_summary(env: EnvironmentConfig) -> str:
    """A compact "host · auth-method" descriptor shown next to each environment name."""
    base_url = str(env.config.base_url)
    host = urlsplit(base_url).netloc or base_url
    return f"{host} · {auth_method_label(env)}"


def environment_line(name: str, *, summary: str, width: int, is_default: bool) -> Text:
    """Render one environment row. Text (not markup) keeps names with "[" literal.

    The current default is prefixed with a bold-green arrow so it stands out in a long list;
    the "host · auth-method" summary trails the (padded) name.
    """
    padded = name.ljust(width)
    if is_default:
        # Chained appends (each returns the Text) keep the whole row in one expression.
        return (
            Text("→ ", style="bold green")
            .append(padded, style="bold green")
            .append(f"   {summary}", style="green")
            .append("  (default)", style="green")
        )
    return Text("  ").append(padded).append(f"   {summary}", style="dim")


def print_environments(console: Console, environments: dict[str, EnvironmentConfig], default: str | None) -> None:
    """List the configured environments with their host/auth summary, marking the default."""
    console.print("Configuration environments:")
    width = max((len(name) for name in environments), default=0)
    for name, env in environments.items():
        console.print(environment_line(name, summary=environment_summary(env), width=width, is_default=name == default))
