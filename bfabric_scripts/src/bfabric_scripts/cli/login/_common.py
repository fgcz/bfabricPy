"""Shared login-parameter resolution for the ``auth`` login commands.

An environment name and OAuth scope may be given on the command line, picked interactively, or --
for the environment -- typed as a new value; whether the environment becomes the config default
is likewise resolved here. Used by ``auth pat`` / ``auth login`` / ``auth device-code``.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bfabric.config.config_file import ConfigFile
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
