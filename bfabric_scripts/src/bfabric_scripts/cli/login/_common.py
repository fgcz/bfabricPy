"""Shared parameter resolution for the ``auth`` login commands.

Both the environment name and the OAuth scope may be given on the command line, picked
interactively, or (for the environment) typed as a new value. This centralizes that logic so
``pkce`` / ``device_code`` / ``pat`` don't each re-implement it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric.config.config_file import ConfigFile
from bfabric_scripts.cli.interactive import is_interactive, resolve_choice, select_choice, text_input

# Named OAuth scope sets. Derived from DEFAULT_OAUTH_SCOPE so the "read-write" baseline and the
# upload variant can't drift from the core default; only the read-only set drops ``api:write``.
_SCOPE_PRESETS: dict[str, str] = {
    "read-only": "api:read openid profile email groups",
    "read-write": DEFAULT_OAUTH_SCOPE,
    "read-write-upload": f"{DEFAULT_OAUTH_SCOPE} tus",
}
_SCOPE_LABELS: dict[str, str] = {
    "read-only": "read-only api",
    "read-write": "read-write api",
    "read-write-upload": "read-write api + upload (tus)",
}
_DEFAULT_SCOPE_PRESET = "read-write"
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
    """Menu label for a scope preset (name + the scopes it maps to) or the Custom entry."""
    width = max(len(label) for label in _SCOPE_LABELS.values())
    if choice == _CUSTOM:
        return f"{'Custom…'.ljust(width)}   (enter scopes manually)"
    return f"{_SCOPE_LABELS[choice].ljust(width)}   {_SCOPE_PRESETS[choice]}"


def resolve_scope(scope: str | None) -> str | None:
    """Resolve the OAuth scope string.

    * *scope* given -> a preset name expands to its scope string; anything else passes through
      as a raw space-separated scope string.
    * no TTY -> the ``read-write`` default (``DEFAULT_OAUTH_SCOPE``).
    * otherwise -> interactive picker of the named presets plus a Custom option that opens a
      free-text prompt. Returns ``None`` if the user cancels.
    """
    if scope is not None:
        return _SCOPE_PRESETS.get(scope, scope)
    if not is_interactive():
        return DEFAULT_OAUTH_SCOPE
    picked = select_choice(
        "Select OAuth scope set",
        [*_SCOPE_PRESETS, _CUSTOM],
        default=_DEFAULT_SCOPE_PRESET,
        describe=_scope_menu_label,
    )
    if picked is None:
        return None
    if picked == _CUSTOM:
        return text_input("Enter OAuth scopes (space-separated)", default=DEFAULT_OAUTH_SCOPE)
    return _SCOPE_PRESETS[picked]
