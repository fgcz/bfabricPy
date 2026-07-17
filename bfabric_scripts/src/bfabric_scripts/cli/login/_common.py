"""Shared helpers for the ``auth`` command group.

Parameter resolution (environment name, OAuth scope, set-default) plus the environment rendering
shared by ``auth default`` / ``auth list`` / ``auth status``.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml
from rich.console import Console
from rich.text import Text

from bfabric.config.config_file import ConfigFile, EnvironmentConfig
from bfabric_scripts.cli.interactive import confirm, is_interactive, select_choice, select_or_input, text_input
from bfabric_scripts.cli.login._constants import SCOPE_PRESETS, SCOPE_PRESETS_BY_NAME

# Interactive-only sentinel: choosing it opens a free-text prompt for raw scopes.
_CUSTOM = "custom"

# Fallback environment name when none is configured and none is given (historical default).
_FALLBACK_ENV = "PRODUCTION"


def resolve_config_env(config_env: str | None, config_file: Path) -> str | None:
    """Resolve the target environment name.

    Explicit *config_env* wins; non-interactive falls back to the current default (else
    ``"PRODUCTION"``); interactive picks an existing name or a typed new one, prefilled with that
    fallback. ``None`` if cancelled.
    """
    if config_env is not None:
        return config_env
    config_path = Path(config_file).expanduser()
    if config_path.is_file():
        loaded = ConfigFile.model_validate(yaml.safe_load(config_path.read_text()))
        names, current = list(loaded.environments), loaded.general.default_config
    else:
        names, current = [], None
    fallback = current or _FALLBACK_ENV
    if not is_interactive():
        return fallback
    return select_or_input("Environment name", names, default=fallback)


def _scope_menu_label(choice: str) -> str:
    """Menu label for a scope preset (description + the scopes it maps to) or the Custom entry."""
    width = max(len(preset.description) for preset in SCOPE_PRESETS)
    if choice == _CUSTOM:
        return f"{'Custom…'.ljust(width)}   (enter scopes manually)"
    preset = SCOPE_PRESETS_BY_NAME[choice]
    return f"{preset.description.ljust(width)}   {preset.scope}"


def resolve_scope(scope: str | None) -> str | None:
    """Resolve the OAuth scope string.

    A given *scope* expands preset names and passes anything else through as a raw scope string.
    Non-interactive returns ``None`` (no default scope, so a headless login must pass ``--scope``;
    the caller aborts). Interactive picks a preset (least-privilege preselected) or Custom
    free-text. ``None`` if cancelled.
    """
    if scope is not None:
        preset = SCOPE_PRESETS_BY_NAME.get(scope)
        return preset.scope if preset is not None else scope
    if not is_interactive():
        return None
    picked = select_choice(
        "Select OAuth scope set",
        [preset.name for preset in SCOPE_PRESETS] + [_CUSTOM],
        default=SCOPE_PRESETS[0].name,
        describe=_scope_menu_label,
    )
    if picked is None:
        return None
    if picked == _CUSTOM:
        return text_input("Enter OAuth scopes (space-separated)")
    return SCOPE_PRESETS_BY_NAME[picked].scope


def resolve_set_default(set_default: bool | None, config_env: str) -> bool | None:
    """Resolve whether the freshly-authenticated environment becomes the config default.

    Explicit *set_default* wins; non-interactive defaults to ``True``; interactive prompts (yes
    preselected). ``None`` if cancelled (the caller aborts).
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

    A preset match (order-insensitive) appends ``[<preset>]``; other non-empty scopes render raw;
    missing / non-string input (a cache without a recorded scope) renders ``"(not recorded)"``.
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
    """Summarize a cached OAuth token's freshness: ``"missing"`` when absent, else ``"present"``,
    extended with ``expired`` / ``expires in ~…`` when it carries a numeric ``expires_at``.
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


def environment_summary(env: EnvironmentConfig) -> str:
    """A compact "host · auth-method" descriptor shown next to each environment name."""
    if env.auth_method in ("oauth", "pat"):
        method = env.auth_method
    elif env.auth is not None:
        method = "password"
    else:
        method = "none"
    base_url = str(env.config.base_url)
    host = urlsplit(base_url).netloc or base_url
    return f"{host} · {method}"


def print_environments(console: Console, environments: dict[str, EnvironmentConfig], default: str | None) -> None:
    """List the configured environments with their host/auth summary, marking the default.

    Rows are built as ``Text`` (not console markup) so a name containing "[" stays literal.
    """
    console.print("Configuration environments:")
    width = max((len(name) for name in environments), default=0)
    for name, env in environments.items():
        padded = name.ljust(width)
        summary = environment_summary(env)
        if name == default:
            row = (
                Text("→ ", style="bold green")
                .append(padded, style="bold green")
                .append(f"   {summary}", style="green")
                .append("  (default)", style="green")
            )
        else:
            row = Text("  ").append(padded).append(f"   {summary}", style="dim")
        console.print(row)
